# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
#
# from app.core.database import get_db
# from . import schemas
# from ...community import model
#
# router = APIRouter(prefix="/communities", tags=["communities"])
#
# @router.post("", response_model=schemas.CommunityRead)
# def create_community(payload: schemas.CommunityCreate, db: Session = Depends(get_db)):
#     m = db.query(model).filter(model.member_id == payload.member_id).first()
#     if not m:
#         raise HTTPException(status_code=400, detail="Invalid member_id")
#
#     c = model(**payload.model_dump())
#     db.add(c)
#     db.commit()
#     db.refresh(c)
#     return c
#
# @router.get("", response_model=list[schemas.CommunityRead])
# def list_communities(member_id: int | None = None, db: Session = Depends(get_db)):
#     q = db.query(model.Community)
#     if member_id is not None:
#         q = q.filter(model.member_id == member_id)
#     return q.order_by(model.community_id.desc()).all()
#
# @router.get("/{community_id}", response_model=schemas.CommunityRead)
# def get_community(community_id: int, db: Session = Depends(get_db)):
#     c = db.query(model).filter(model.community_id == community_id).first()
#     if not c:
#         raise HTTPException(status_code=404, detail="Community not found")
#     return c
#
# @router.delete("/{community_id}")
# def delete_community(community_id: int, db: Session = Depends(get_db)):
#     c = db.query(model).filter(model.community_id == community_id).first()
#     if not c:
#         raise HTTPException(status_code=404, detail="Community not found")
#     db.delete(c)
#     db.commit()
#     return {"deleted": True, "community_id": community_id}
