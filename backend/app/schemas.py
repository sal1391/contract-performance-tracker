"""Pydantic API schemas (read models for the skeleton)."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ContractRead(ORMModel):
    id: uuid.UUID
    contract_source_id: str
    customer_group_number: str
    customer_group_name: str | None = None
    bid_year: int | None = None
    region: str | None = None
    source_status: str | None = None
    bid_sub_note: str | None = None
    source_system: str | None = None
    office_id: uuid.UUID | None = None


class BidLineRead(ORMModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    port: str
    grade: str | None = None
    supplier_name: str | None = None
    contracted_volume: float | None = None
    margin: float | None = None
    gross_profit: float | None = None
    bid_status: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None


class LiftMapRead(ORMModel):
    id: uuid.UUID
    bid_line_id: uuid.UUID
    lift_id: str
    status: str
    match_score: float | None = None
    override_reason: str | None = None


class MappingCreate(BaseModel):
    bid_line_id: uuid.UUID
    lift_id: str
    override_reason: str | None = None


class DashboardSummary(BaseModel):
    by_status: dict[str, int]
    gp_at_risk: float


class RiskLine(BaseModel):
    """One bid line at a given risk status, with its contract context (dashboard drill-down)."""
    bid_line_id: uuid.UUID
    contract_id: uuid.UUID
    contract_source_id: str | None = None
    customer_group_number: str | None = None
    customer_group_name: str | None = None
    port: str | None = None
    grade: str | None = None
    supplier_name: str | None = None
    risk_status: str
    contracted_volume: float | None = None
    actual_volume: float | None = None
    contracted_gp: float | None = None
    actual_gp: float | None = None
    elapsed_pct: float | None = None
    contract_end: date | None = None


class ContractCreate(BaseModel):
    contract_source_id: str            # the QB ID (header)
    customer_group_number: str         # CLIENT
    customer_group_name: str | None = None
    bid_year: int | None = None        # BID YEAR
    region: str | None = None          # REGION
    source_status: str | None = None   # QB STATUS
    bid_sub_note: str | None = None    # Bid sub note
    office_id: uuid.UUID | None = None # which office owns it (drives RLS); defaults to creator's
    source_system: str = "MANUAL"      # hand-entered in-app; intake rows arrive as QUICKBASE


class BidLineCreate(BaseModel):
    contract_id: uuid.UUID
    owner_user_id: uuid.UUID | None = None   # customer broker; defaults to the acting user
    port: str                          # PORT
    grade: str | None = None           # GRADE
    supplier_number: str | None = None # SUPPLIER
    supplier_name: str | None = None
    index_symbol: str | None = None    # INDEX
    formula: str | None = None         # FORMULA
    price_uom: str | None = None       # PRICE UOM
    selling_premium: float | None = None   # SELLING PREMIUM
    buying_premium: float | None = None    # BUYING PREMIUM
    freight_type: str | None = None    # FREIGHT
    pricing_days: str | None = None    # PRICING DAYS
    supplier_terms: str | None = None  # SUPPLIER TERMS
    contracted_volume: float | None = None  # CONTRACTED VOLUME
    volume_tolerance: str | None = None     # VOLUME TOLERANCE (free-text note)
    tolerance_pct: float | None = None      # Tol. +/- as a fraction (0.10 = 10%); drives at-risk
    supply_method: str | None = None   # SUPPLY METHOD
    spec: str | None = None            # SPEC
    contract_start: date | None = None # CONTRACT START
    contract_end: date | None = None   # CONTRACT END
    date_offered: date | None = None   # DATE OFFERED
    freight_fee: str | None = None     # FREIGHT FEE
    notes: str | None = None           # NOTES
    bid_notes: str | None = None       # BID NOTES
    bid_status: str | None = None      # BID STATUS
    # MARGIN and GROSS PROFIT are computed in the DB, not entered.


class ContractUpdate(BaseModel):
    contract_source_id: str | None = None
    customer_group_number: str | None = None
    customer_group_name: str | None = None
    bid_year: int | None = None
    region: str | None = None
    source_status: str | None = None
    bid_sub_note: str | None = None


class BidLineUpdate(BaseModel):
    port: str | None = None
    grade: str | None = None
    supplier_number: str | None = None
    supplier_name: str | None = None
    index_symbol: str | None = None
    formula: str | None = None
    price_uom: str | None = None
    selling_premium: float | None = None
    buying_premium: float | None = None
    freight_type: str | None = None
    pricing_days: str | None = None
    supplier_terms: str | None = None
    contracted_volume: float | None = None
    volume_tolerance: str | None = None
    tolerance_pct: float | None = None
    owner_user_id: uuid.UUID | None = None
    supply_method: str | None = None
    spec: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None
    date_offered: date | None = None
    freight_fee: str | None = None
    notes: str | None = None
    bid_notes: str | None = None
    bid_status: str | None = None


class BidLineRow(ORMModel):
    """Bid line + its contract context (QB ID / customer), for the workbench + mapping dropdown."""
    id: uuid.UUID
    contract_id: uuid.UUID
    contract_source_id: str | None = None   # QB ID — what the line belongs to
    customer_group_name: str | None = None
    owner_user_id: uuid.UUID | None = None   # customer broker (attribution; not RLS)
    port: str | None = None
    grade: str | None = None
    supplier_number: str | None = None
    supplier_name: str | None = None
    index_symbol: str | None = None
    formula: str | None = None
    price_uom: str | None = None
    selling_premium: float | None = None
    buying_premium: float | None = None
    margin: float | None = None
    freight_type: str | None = None
    pricing_days: str | None = None
    supplier_terms: str | None = None
    contracted_volume: float | None = None
    volume_tolerance: str | None = None
    tolerance_pct: float | None = None
    gross_profit: float | None = None
    supply_method: str | None = None
    spec: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None
    date_offered: date | None = None
    freight_fee: str | None = None
    notes: str | None = None
    bid_notes: str | None = None
    bid_status: str | None = None


class LiftRead(ORMModel):
    lift_id: str
    customer_group_number: str | None = None
    supplier_number: str | None = None
    port: str | None = None
    grade: str | None = None
    lift_date: date | None = None
    volume_tons: float | None = None
    gp: float | None = None


# --------------------------------------------------------------------------- org tree / users
UNIT_TYPES = ("COMPANY", "SEGMENT", "REGION", "OFFICE")
ROLE_LEVELS = ("IC", "OFFICE_MANAGER", "REGIONAL_DIRECTOR", "SEGMENT_LEAD", "LEADERSHIP", "ADMIN")


class OrgUnitRead(ORMModel):
    id: uuid.UUID
    name: str
    unit_type: str
    parent_id: uuid.UUID | None = None
    is_active: bool = True
    is_verified: bool = True


class OrgUnitCreate(BaseModel):
    name: str
    unit_type: str
    parent_id: uuid.UUID | None = None


class OrgUnitUpdate(BaseModel):
    name: str | None = None
    unit_type: str | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None


class AppUserRead(ORMModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    role_level: str
    home_office_id: uuid.UUID | None = None
    scope_unit_id: uuid.UUID | None = None
    is_active: bool = True
    source: str = "MANUAL"
    source_broker_id: str | None = None
    role_locked: bool = False


class AppUserCreate(BaseModel):
    email: str
    display_name: str | None = None
    role_level: str = "IC"
    home_office_id: uuid.UUID | None = None
    scope_unit_id: uuid.UUID | None = None
    auth0_sub: str | None = None   # defaults to "dev|<email>" so the act-as switch can find them


class AppUserUpdate(BaseModel):
    display_name: str | None = None
    role_level: str | None = None
    home_office_id: uuid.UUID | None = None
    scope_unit_id: uuid.UUID | None = None
    is_active: bool | None = None
    role_locked: bool | None = None


class DevUser(ORMModel):
    """Minimal projection for the dev 'act as user' dropdown."""
    id: uuid.UUID
    email: str
    display_name: str | None = None
    role_level: str
    scope_unit_id: uuid.UUID | None = None


class OrgUnitMerge(BaseModel):
    into_id: uuid.UUID


class BrokerOption(ORMModel):
    id: uuid.UUID
    display_name: str | None = None
    email: str


class SyncResult(BaseModel):
    status: str
    reason: str | None = None
    units_created: int | None = None
    users_created: int | None = None
    users_updated: int | None = None


# --------------------------------------------------------------------------- accounts / CRM
class AccountSummary(BaseModel):
    customer_group_number: str
    customer_group_name: str | None = None
    contract_count: int
    line_count: int
    gp_won: float
    gp_pending: float
    gp_lost: float
    win_rate: float | None = None
    volume_won: float
    volume_pending: float


class AccountLine(ORMModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    port: str
    grade: str | None = None
    supplier_name: str | None = None
    bid_status: str | None = None
    risk_status: str | None = None      # from bid_line_performance view (may be unavailable)
    contracted_volume: float | None = None
    gross_profit: float | None = None
    margin: float | None = None


class AccountContract(ORMModel):
    id: uuid.UUID
    contract_source_id: str
    bid_year: int | None = None
    region: str | None = None
    source_status: str | None = None
    risk_status: str | None = None      # worst risk across the contract's visible lines
    lines: list[AccountLine] = []


class AccountDetail(BaseModel):
    summary: AccountSummary
    contracts: list[AccountContract]
