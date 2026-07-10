"""SQLAlchemy models — mirrors docs/snowflake/COCO_BUILD_SPEC.md Part B (+ session-2 additions).

Standard PostgreSQL; runs on local Postgres in dev and Snowflake Postgres in prod.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Computed, Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

unit_type_enum = Enum("COMPANY", "SEGMENT", "REGION", "OFFICE", name="unit_type")
role_level_enum = Enum("IC", "OFFICE_MANAGER", "REGIONAL_DIRECTOR", "SEGMENT_LEAD",
                       "LEADERSHIP", "ADMIN", name="role_level")
source_system_enum = Enum("QUICKBASE", "DOCUSIGN", "MANUAL", name="source_system")
map_status_enum = Enum("AUTO_SUGGESTED", "CONFIRMED", "USER_ADDED", "EXCLUDED", name="map_status")
user_source_enum = Enum("SYNCED", "MANUAL", name="user_source")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def _updated() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# --------------------------------------------------------------------------- org hierarchy
class OrgUnit(Base):
    __tablename__ = "org_unit"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    unit_type: Mapped[str] = mapped_column(unit_type_enum, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)  # sync auto-creates -> False
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class OrgClosure(Base):
    __tablename__ = "org_closure"
    ancestor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_unit.id", ondelete="CASCADE"), primary_key=True)
    descendant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_unit.id", ondelete="CASCADE"), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)


# --------------------------------------------------------------------------- users
class AppUser(Base):
    __tablename__ = "app_user"
    id: Mapped[uuid.UUID] = _pk()
    auth0_sub: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    role_level: Mapped[str] = mapped_column(role_level_enum, default="IC", nullable=False)
    home_office_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    scope_unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    source: Mapped[str] = mapped_column(user_source_enum, default="MANUAL", nullable=False)
    source_broker_id: Mapped[str | None] = mapped_column(Text)   # sales-planning customer_broker_number
    role_locked: Mapped[bool] = mapped_column(Boolean, default=False)  # admin override; sync won't reset
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


# --------------------------------------------------------------------------- contracts / lines
class Contract(Base):
    __tablename__ = "contract"
    __table_args__ = (UniqueConstraint("source_system", "contract_source_id"),)
    id: Mapped[uuid.UUID] = _pk()
    contract_source_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_system: Mapped[str] = mapped_column(source_system_enum, default="QUICKBASE", nullable=False)
    customer_group_number: Mapped[str] = mapped_column(Text, nullable=False)
    customer_group_name: Mapped[str | None] = mapped_column(Text)
    bid_year: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[str | None] = mapped_column(Text)
    source_status: Mapped[str | None] = mapped_column(Text)      # QB STATUS (header)
    bid_sub_note: Mapped[str | None] = mapped_column(Text)       # Bid sub note (header)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    office_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    bid_lines: Mapped[list["BidLine"]] = relationship(back_populates="contract",
                                                       cascade="all, delete-orphan")


class BidLine(Base):
    __tablename__ = "bid_line"
    __table_args__ = (
        UniqueConstraint("contract_id", "port", "grade", "supplier_number"),
        CheckConstraint(
            "contract_end IS NULL OR contract_start IS NULL OR contract_end >= contract_start",
            name="chk_dates"),
    )
    id: Mapped[uuid.UUID] = _pk()
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract.id", ondelete="CASCADE"), nullable=False)
    port: Mapped[str] = mapped_column(Text, nullable=False)
    grade: Mapped[str | None] = mapped_column(Text)
    supplier_number: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(Text)
    index_symbol: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)
    price_uom: Mapped[str | None] = mapped_column(ForeignKey("lkp_price_uom.code"))
    selling_premium: Mapped[float | None] = mapped_column(Numeric(18, 4))
    buying_premium: Mapped[float | None] = mapped_column(Numeric(18, 4))
    margin: Mapped[float | None] = mapped_column(
        Numeric(18, 4), Computed("selling_premium - buying_premium", persisted=True))
    freight_type: Mapped[str | None] = mapped_column(ForeignKey("lkp_freight_type.code"))
    pricing_days: Mapped[str | None] = mapped_column(ForeignKey("lkp_pricing_days.code"))
    supplier_terms: Mapped[str | None] = mapped_column(Text)
    contracted_volume: Mapped[float | None] = mapped_column(Numeric(18, 3))
    volume_tolerance: Mapped[str | None] = mapped_column(Text)
    tolerance_pct: Mapped[float] = mapped_column(Numeric(6, 4), default=0.10)
    gross_profit: Mapped[float | None] = mapped_column(
        Numeric(20, 2),
        Computed("contracted_volume * (selling_premium - buying_premium)", persisted=True))
    supply_method: Mapped[str | None] = mapped_column(ForeignKey("lkp_supply_method.code"))
    spec: Mapped[str | None] = mapped_column(Text)
    contract_start: Mapped[date | None] = mapped_column(Date)
    contract_end: Mapped[date | None] = mapped_column(Date)
    date_offered: Mapped[date | None] = mapped_column(Date)
    freight_fee: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    bid_notes: Mapped[str | None] = mapped_column(Text)
    bid_sub_note: Mapped[str | None] = mapped_column(Text)
    bid_status: Mapped[str | None] = mapped_column(ForeignKey("lkp_bid_status.code"))
    qb_id: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    office_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()
    contract: Mapped["Contract"] = relationship(back_populates="bid_lines")


class LiftContractMap(Base):
    __tablename__ = "lift_contract_map"
    __table_args__ = (UniqueConstraint("bid_line_id", "lift_id"),)
    id: Mapped[uuid.UUID] = _pk()
    bid_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bid_line.id", ondelete="CASCADE"), nullable=False)
    lift_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(map_status_enum, default="AUTO_SUGGESTED", nullable=False)
    match_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    override_reason: Mapped[str | None] = mapped_column(Text)
    # denormalized LIFT facts (captured by the matcher -> performance is pure-Postgres):
    lift_lift_date: Mapped[date | None] = mapped_column(Date)
    lift_volume_tons: Mapped[float | None] = mapped_column(Numeric(18, 3))
    lift_gp: Mapped[float | None] = mapped_column(Numeric(20, 2))
    mapped_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    mapped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


# --------------------------------------------------------------------------- lookups
class _Lookup:
    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LkpPriceUom(_Lookup, Base):
    __tablename__ = "lkp_price_uom"


class LkpFreightType(_Lookup, Base):
    __tablename__ = "lkp_freight_type"


class LkpPricingDays(_Lookup, Base):
    __tablename__ = "lkp_pricing_days"


class LkpBidStatus(_Lookup, Base):
    __tablename__ = "lkp_bid_status"


class LkpSupplyMethod(_Lookup, Base):
    __tablename__ = "lkp_supply_method"


# --------------------------------------------------------------------------- dimensions (synced from Snowflake)
class DimPort(Base):
    __tablename__ = "dim_port"
    port: Mapped[str] = mapped_column(Text, primary_key=True)
    region: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = _created()


class DimCustomer(Base):
    __tablename__ = "dim_customer"
    customer_group_number: Mapped[str] = mapped_column(Text, primary_key=True)
    customer_group_name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = _created()


class DimSupplier(Base):
    __tablename__ = "dim_supplier"
    supplier_number: Mapped[str] = mapped_column(Text, primary_key=True)
    supplier_name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = _created()


class DimGrade(Base):
    __tablename__ = "dim_grade"
    grade: Mapped[str] = mapped_column(Text, primary_key=True)
    grade_group: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = _created()


class DimIndex(Base):
    __tablename__ = "dim_index"
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    index_name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = _created()


# --------------------------------------------------------------------------- audit / config
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    changed_at: Mapped[datetime] = _created()
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)


class SegmentViewConfig(Base):
    __tablename__ = "segment_view_config"
    id: Mapped[uuid.UUID] = _pk()
    segment_unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class LiftSource(Base):
    """LOCAL/dev stand-in for Snowflake LIFTS_FOR_MATCHING_V so the matcher + mapping work
    without Snowflake. In prod these rows come from Snowflake, not this table."""
    __tablename__ = "lift_source"
    lift_id: Mapped[str] = mapped_column(Text, primary_key=True)
    customer_group_number: Mapped[str | None] = mapped_column(Text)
    supplier_number: Mapped[str | None] = mapped_column(Text)
    port: Mapped[str | None] = mapped_column(Text)
    grade: Mapped[str | None] = mapped_column(Text)
    lift_date: Mapped[date | None] = mapped_column(Date)
    volume_tons: Mapped[float | None] = mapped_column(Numeric(18, 3))
    gp: Mapped[float | None] = mapped_column(Numeric(20, 2))
