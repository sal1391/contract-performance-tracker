"""Contract intake sync: Snowflake CONTRACT_INTAKE -> Postgres contract/bid_line.

Group intake rows by CONTRACT_SOURCE_ID (fallback customer_group_number + bid_year) -> upsert
`contract`; per row -> upsert `bid_line`. PRESERVE user-entered fields (premiums, notes, etc.):
only populate them from intake when currently null. See COCO_BUILD_SPEC.md Part D.
"""
from __future__ import annotations

# Fields the team owns in-app — intake must never overwrite these once set.
USER_OWNED_FIELDS = (
    "selling_premium", "buying_premium", "tolerance_pct", "freight_fee",
    "notes", "bid_notes", "bid_sub_note", "index_symbol", "formula",
)


def sync_contract_intake(db, sf_conn=None) -> dict[str, int]:
    """Returns counts of contracts/bid_lines upserted. Raises without a Snowflake connection."""
    if sf_conn is None:
        raise RuntimeError(
            "sync_contract_intake needs a Snowflake connection; run on the Snowflake-connected machine."
        )
    # TODO(coco):
    #   rows = SELECT * FROM CONTRACT_INTAKE
    #   group by CONTRACT_SOURCE_ID -> upsert contract on (source_system, contract_source_id)
    #   per row -> upsert bid_line on (contract_id, port, grade, supplier_number)
    #   for USER_OWNED_FIELDS: set from intake only when the existing value IS NULL
    # classification: set contract.office_id = resolve_office_id(<QB office col>, office_id_by_name)
    #   from app.services.org_sync, where office_id_by_name = {u.name: u.id for OFFICE org_units}.
    # Lines + Lifts inherit contract.office_id (already enforced in routers/bid_lines).
    raise NotImplementedError("Implement intake upsert on the connected machine.")
