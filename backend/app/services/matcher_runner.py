"""DB+Snowflake runner around the pure matcher in app.services.matcher.

Pulls candidate Lifts from Snowflake LIFTS_FOR_MATCHING_V, suggests matches against active
bid_lines, and upserts AUTO_SUGGESTED rows — never overwriting CONFIRMED/USER_ADDED/EXCLUDED.
"""
from __future__ import annotations


def run_matcher(db, sf_conn=None) -> int:
    """Returns number of AUTO_SUGGESTED rows written. Raises without a Snowflake connection."""
    if sf_conn is None:
        raise RuntimeError(
            "run_matcher needs a Snowflake connection; run on the Snowflake-connected machine."
        )
    # TODO(coco) — wire the pure logic to real data:
    #   from app.services.matcher import Lift, BidLine, suggest_matches
    #   lifts  = [Lift(...) for r in sf_conn.cursor().execute("SELECT * FROM LIFTS_FOR_MATCHING_V ...")]
    #   lines = [BidLine(...) from db active bid_line rows]
    #   for s in suggest_matches(lifts, lines, grade_groups):
    #       upsert lift_contract_map(bid_line_id, lift_id) status=AUTO_SUGGESTED, match_score=s.score,
    #         lift_lift_date/lift_volume_tons/lift_gp from the LIFT row;
    #       ON CONFLICT (bid_line_id, lift_id) DO NOTHING  -- preserves human edits
    raise NotImplementedError("Implement the matcher upsert on the connected machine.")


def run_matcher_local(db, bid_line_id=None) -> int:
    """LOCAL/dev matcher: reads the lift_source table (Snowflake stand-in) and writes
    AUTO_SUGGESTED rows, never overwriting human edits. Returns count created."""
    from sqlalchemy import select

    from app.models import BidLine, LiftContractMap, LiftSource
    from app.services.matcher import BidLine as MLine
    from app.services.matcher import Lift, suggest_matches

    bl_stmt = select(BidLine)
    if bid_line_id:
        bl_stmt = bl_stmt.where(BidLine.id == bid_line_id)
    lines = db.scalars(bl_stmt).all()

    lift_rows = db.scalars(select(LiftSource)).all()
    lift_by_id = {p.lift_id: p for p in lift_rows}
    lifts = [
        Lift(lift_id=p.lift_id, customer_group_number=p.customer_group_number or "",
            supplier_number=p.supplier_number, port=p.port or "", grade=p.grade,
            lift_date=p.lift_date, volume_tons=float(p.volume_tons or 0), gp=float(p.gp or 0))
        for p in lift_rows if p.lift_date is not None
    ]

    mlines = []
    for line in lines:
        if line.contract_start is None or line.contract_end is None:
            continue
        cust = line.contract.customer_group_number if line.contract else ""
        mlines.append(MLine(
            id=str(line.id), customer_group_number=cust, supplier_number=line.supplier_number,
            port=line.port or "", grade=line.grade,
            contract_start=line.contract_start, contract_end=line.contract_end,
        ))

    created = 0
    for s in suggest_matches(lifts, mlines):
        exists = db.scalar(select(LiftContractMap).where(
            LiftContractMap.bid_line_id == s.bid_line_id,
            LiftContractMap.lift_id == s.lift_id))
        if exists:
            continue
        p = lift_by_id.get(s.lift_id)
        db.add(LiftContractMap(
            bid_line_id=s.bid_line_id, lift_id=s.lift_id, status="AUTO_SUGGESTED",
            match_score=s.score,
            lift_lift_date=p.lift_date if p else None,
            lift_volume_tons=p.volume_tons if p else None,
            lift_gp=p.gp if p else None,
        ))
        created += 1
    db.commit()
    return created
