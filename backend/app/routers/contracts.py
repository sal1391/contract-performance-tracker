from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import ScopeContext, get_scope
from app.db import get_db
from app.deps import scoped_filter
from app.models import Contract
from app.schemas import ContractCreate, ContractRead, ContractUpdate

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractRead])
def list_contracts(
    db: Session = Depends(get_db),
    scope: ScopeContext = Depends(get_scope),
    q: str | None = Query(default=None, description="search QB ID / customer"),
):
    stmt = scoped_filter(select(Contract), Contract.office_id, scope)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            Contract.contract_source_id.ilike(like),
            Contract.customer_group_number.ilike(like),
            Contract.customer_group_name.ilike(like),
        ))
    return db.scalars(stmt.order_by(Contract.created_at.desc()).limit(500)).all()


@router.post("", response_model=ContractRead, status_code=201)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db),
                    scope: ScopeContext = Depends(get_scope)):
    """Enter a new bid/contract keyed by its QB ID (contract_source_id).

    Stamps the owning office (RLS key): the explicit office_id if given, else the acting
    user's home office. Without an office, only see-everything users would find the bid.
    """
    data = payload.model_dump()
    office_id = data.pop("office_id", None) or scope.home_office_id
    contract = Contract(**data, office_id=office_id, owner_user_id=scope.app_user_id)
    db.add(contract)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A contract with QB ID '{payload.contract_source_id}' already exists")
    db.refresh(contract)
    return contract


@router.patch("/{contract_id}", response_model=ContractRead)
def update_contract(contract_id: str, payload: ContractUpdate, db: Session = Depends(get_db),
                    scope: ScopeContext = Depends(get_scope)):
    q = scoped_filter(select(Contract).where(Contract.id == contract_id),
                      Contract.office_id, scope)
    c = db.scalars(q).first()
    if c is None:
        raise HTTPException(404, "Contract not found or not in your scope")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That QB ID is already used by another contract")
    db.refresh(c)
    return c


@router.get("/{contract_id}", response_model=ContractRead)
def get_contract(contract_id: str, db: Session = Depends(get_db),
                 scope: ScopeContext = Depends(get_scope)):
    q = scoped_filter(select(Contract).where(Contract.id == contract_id),
                      Contract.office_id, scope)
    row = db.scalars(q).first()
    if row is None:
        raise HTTPException(404, "Contract not found or not in your scope")
    return row


@router.delete("/{contract_id}", status_code=204)
def delete_contract(contract_id: str, db: Session = Depends(get_db),
                    scope: ScopeContext = Depends(get_scope)):
    """Delete a contract and (cascade) its bid lines + their LIFT mappings."""
    q = scoped_filter(select(Contract).where(Contract.id == contract_id),
                      Contract.office_id, scope)
    c = db.scalars(q).first()
    if c is None:
        raise HTTPException(404, "Contract not found or not in your scope")
    db.delete(c)
    db.commit()
