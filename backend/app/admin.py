"""sqladmin auto-admin for the org/user/lookup tables — the Django-admin equivalent.

TODO(prod): gate /admin behind the ADMIN role using a sqladmin AuthenticationBackend that
validates the Auth0 session. Open in local dev.
"""
from sqladmin import Admin, ModelView

from app.models import (
    AppUser, LkpBidStatus, LkpFreightType, LkpPriceUom, LkpPricingDays, LkpSupplyMethod,
    OrgUnit, SegmentViewConfig,
)


class AppUserAdmin(ModelView, model=AppUser):
    name_plural = "Users"
    column_list = [AppUser.email, AppUser.role_level, AppUser.home_office_id,
                   AppUser.scope_unit_id, AppUser.is_active]


def _rebuild_closure() -> None:
    """Keep org_closure in sync after org edits made through /admin (the React Admin page
    and /org API already do this; this covers the sqladmin path too)."""
    from app.db import SessionLocal
    from app.services.org import rebuild_closure
    db = SessionLocal()
    try:
        rebuild_closure(db)
    finally:
        db.close()


class OrgUnitAdmin(ModelView, model=OrgUnit):
    name_plural = "Org Units"
    column_list = [OrgUnit.name, OrgUnit.unit_type, OrgUnit.parent_id, OrgUnit.is_active]

    # signatures vary across sqladmin versions -> accept anything, just trigger a rebuild
    async def after_model_change(self, *args, **kwargs):  # noqa: ANN001, ANN201
        _rebuild_closure()

    async def after_model_delete(self, *args, **kwargs):  # noqa: ANN001, ANN201
        _rebuild_closure()


class _LkpAdmin(ModelView):
    column_list = ["code", "label", "sort_order", "is_active"]


class PriceUomAdmin(_LkpAdmin, model=LkpPriceUom): ...
class FreightTypeAdmin(_LkpAdmin, model=LkpFreightType): ...
class PricingDaysAdmin(_LkpAdmin, model=LkpPricingDays): ...
class BidStatusAdmin(_LkpAdmin, model=LkpBidStatus): ...
class SupplyMethodAdmin(_LkpAdmin, model=LkpSupplyMethod): ...
class SegmentViewConfigAdmin(ModelView, model=SegmentViewConfig):
    column_list = [SegmentViewConfig.segment_unit_id, SegmentViewConfig.config]


def setup_admin(app, engine) -> Admin:
    admin = Admin(app, engine, title="Contract Tracker Admin")
    for view in (AppUserAdmin, OrgUnitAdmin, PriceUomAdmin, FreightTypeAdmin,
                 PricingDaysAdmin, BidStatusAdmin, SupplyMethodAdmin, SegmentViewConfigAdmin):
        admin.add_view(view)
    return admin
