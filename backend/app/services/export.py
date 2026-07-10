"""Performance export: Postgres -> Snowflake reporting tables (every few hours).

MERGE current state into CONTRACTS_APP.CONTRACT_PERFORMANCE and APPEND the same rows to
CONTRACT_PERFORMANCE_HISTORY (the point-in-time backup copy). See COCO_BUILD_SPEC.md Part H.
"""
from __future__ import annotations


def export_performance(db, sf_conn=None, snapshot_at=None) -> int:
    """Returns number of rows exported. Raises without a Snowflake connection."""
    if sf_conn is None:
        raise RuntimeError(
            "export_performance needs a Snowflake connection; run on the Snowflake-connected machine."
        )
    # TODO(coco):
    #   rows = SELECT ... FROM bid_line_performance p JOIN bid_line bl ... JOIN contract c ...
    #   MERGE INTO CONTRACTS_APP.CONTRACT_PERFORMANCE USING (rows) ON BID_LINE_ID ...
    #   INSERT INTO CONTRACTS_APP.CONTRACT_PERFORMANCE_HISTORY SELECT *, :snapshot_at
    raise NotImplementedError("Implement Postgres->Snowflake export on the connected machine.")
