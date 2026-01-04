from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/member-restrictions", tags=["member-restrictions"])

@router.post("", response_model=schemas.MemberRestrictionRead)
def add_member_restriction(payload: schemas.MemberRestrictionCreate, db: Session = Depends(get_db)):
    m = db.query(models.Member).filter(models.Member.member_id == payload.member_id).first()
    if not m:
        raise HTTPException(status_code=400, detail="Invalid member_id")

    it = db.query(models.RestrictionItems).filter(models.RestrictionItems.item_id == payload.item_id).first()
    if not it:
        raise HTTPException(status_code=400, detail="Invalid item_id")

    mr = models.MemberRestrictions(**payload.model_dump())
    db.add(mr)
    try:
        db.commit()
        db.refresh(mr)
        return mr
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Already assigned (member_id, item_id)")

@router.get("", response_model=list[schemas.MemberRestrictionRead])
def list_member_restrictions(member_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.MemberRestrictions)
    if member_id is not None:
        q = q.filter(models.MemberRestrictions.member_id == member_id)
    return q.order_by(models.MemberRestrictions.member_restrictions_id.asc()).all()

@router.delete("/{member_restrictions_id}")
def delete_member_restriction(member_restrictions_id: int, db: Session = Depends(get_db)):
    mr = db.query(models.MemberRestrictions).filter(
        models.MemberRestrictions.member_restrictions_id == member_restrictions_id
    ).first()
    if not mr:
        raise HTTPException(status_code=404, detail="Member restriction not found")

    db.delete(mr)
    db.commit()
    return {"deleted": True, "member_restrictions_id": member_restrictions_id}
