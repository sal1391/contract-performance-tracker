"""Dimension sync: Snowflake -> Postgres dim_* tables.

The distinct SELECTs run against Snowflake (only on the Snowflake-connected machine) and are
upserted into Postgres. `‹…›` placeholders mirror COCO_BUILD_SPEC.md §0 / Part F and must be
finalized once the real SALES_ACTUALS_V column names are confirmed.
"""
from __future__ import annotations

# (Snowflake SQL) distinct source queries -> upsert target table
SNOWFLAKE_DIM_QUERIES: dict[str, str] = {
    "dim_port": "SELECT DISTINCT PORT_NAME AS PORT, ‹REGION_EXPR› AS REGION "
                "FROM SALES_ACTUALS_V WHERE PORT_NAME IS NOT NULL",
    "dim_customer": "SELECT DISTINCT ‹CUSTOMER_GROUP_NUMBER› AS CUSTOMER_GROUP_NUMBER, "
                    "CUSTOMER_NAME AS CUSTOMER_GROUP_NAME FROM SALES_ACTUALS_V "
                    "WHERE ‹CUSTOMER_GROUP_NUMBER› IS NOT NULL",
    "dim_supplier": "SELECT DISTINCT ‹SUPPLIER_NUMBER› AS SUPPLIER_NUMBER, "
                    "SUPPLIER_NAME AS SUPPLIER_NAME FROM SALES_ACTUALS_V "
                    "WHERE ‹SUPPLIER_NUMBER› IS NOT NULL",
    "dim_grade": "SELECT DISTINCT ‹GRADE_NAME› AS GRADE, ‹GRADE_GROUP_EXPR› AS GRADE_GROUP "
                 "FROM SALES_ACTUALS_V WHERE ‹GRADE_NAME› IS NOT NULL",
    "dim_index": "SELECT DISTINCT SYMBOL, ‹INDEX_NAME_EXPR› AS INDEX_NAME "
                 "FROM MARKET_PRICES_HISTORY_V WHERE SYMBOL IS NOT NULL",
}


def refresh_dimensions(db, sf_conn=None) -> dict[str, int]:
    """Pull each dimension from Snowflake and upsert into Postgres (ON CONFLICT DO UPDATE),
    soft-deactivating values no longer present. Returns row counts per table.

    Raises if no Snowflake connection (i.e. running on a machine without Snowflake access).
    """
    if sf_conn is None:
        raise RuntimeError(
            "refresh_dimensions needs a Snowflake connection; run on the Snowflake-connected machine."
        )
    # TODO(coco): for each (table, query): cur.execute(query); rows = cur.fetchall();
    #   upsert into dim_* with ON CONFLICT (pk) DO UPDATE SET ..., synced_at = now();
    #   UPDATE dim_* SET is_active = FALSE WHERE pk NOT IN (synced pks).
    raise NotImplementedError("Implement Snowflake->Postgres upsert on the connected machine.")
