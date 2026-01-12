from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.member import Member
from app.models.restrictions.item import Item
from app.models.restrictions.dislike import Dislike
from app.models.restrictions.member_restriction import MemberRestrictions

import json

# 등록
def create_member(db: Session, payload) -> None:
    # db.begin() :: commit, reset 둘중 처리
    print(payload)

    try:
        with db.begin():
            # item_ids / dislike 제외하고 member 조회
            member_data = payload.model_dump(exclude={"item_ids", "dislike_tags"})
            member = Member(**member_data)
            db.add(member)
            db.flush()

            member_id = member.member_id

            # item_ids는 None/[]면 스킵
            if payload.item_ids:
                req_ids = set(payload.item_ids)
                found = set(db.execute(
                    select(Item.item_id).where(Item.item_id.in_(req_ids))
                ).scalars().all())
                missing = sorted(req_ids - found)
                if missing:
                    raise HTTPException(400, detail={"message": "invalid item_ids", "missing_item_ids": missing})

                db.add_all([MemberRestrictions(member_id=member_id, item_id=i) for i in sorted(req_ids)])

            # dislike_tag 비선호 추가 부분
            if payload.dislike_tags is not None and len(payload.dislike_tags) > 0:
                if isinstance(payload.dislike_tags, list):
                    tag_json = json.dumps(payload.dislike_tags, ensure_ascii=False)
                db.add(Dislike(member_id=member_id, dislike_tag=tag_json))

    except IntegrityError:
        raise HTTPException(409, detail="duplicate key")

# 조회
def get_member(db: Session, member_id: int) -> dict:
    print(member_id)

    m = db.get(Member, member_id)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    item_ids = db.execute(
        select(MemberRestrictions.item_id).where(MemberRestrictions.member_id == member_id)
    ).scalars().all()

    tag_raw = db.execute(
        select(Dislike.dislike_tag).where(Dislike.member_id == member_id)
    ).scalar_one_or_none()
    print("tag_raw :: ", tag_raw)

    # dislike_tags = None
    # if tag_raw is not None:
    #     # DB에 JSON 문자열로 저장했으니 리스트로 복원
    #     dislike_tags = json.loads(tag_raw)

    dislike_tags = None
    if tag_raw is not None:
        try:
            dislike_tags = json.loads(tag_raw)
        except Exception:
            dislike_tags = [tag_raw]  # 혹시 그냥 문자열이면 방어

    return {
        "email": m.email,
        "nickname": m.nickname,
        "gender": m.gender,
        "country": m.country,
        "item_ids": item_ids,
        "dislike_tags": dislike_tags,
    }

# 수정
def update_member(db: Session, member_id: int, payload):

    print(payload)

    try:
        with db.begin():
            m = db.get(Member, member_id)
            if not m:
                raise HTTPException(404, detail="Member not found")

            # nickname 변경(필요 시 유니크 체크)
            if payload.nickname is not None and payload.nickname != m.nickname:
                exists = db.execute(
                    select(Member.member_id).where(Member.nickname == payload.nickname, Member.member_id != member_id)
                ).scalar_one_or_none()
                if exists is not None:
                    raise HTTPException(409, detail="nickname already exists")
                m.nickname = payload.nickname

            # item_ids: None=변경없음 / []=전체해제 / [..]=replace
            if payload.item_ids is not None:
                new_ids = set(payload.item_ids)
                old_ids = set(db.execute(
                    select(MemberRestrictions.item_id).where(MemberRestrictions.member_id == member_id)
                ).scalars().all())

                if new_ids != old_ids:
                    if new_ids:
                        found = set(db.execute(
                            select(Item.item_id).where(Item.item_id.in_(new_ids))
                        ).scalars().all())
                        missing = sorted(new_ids - found)
                        if missing:
                            raise HTTPException(400, detail={"message": "invalid item_ids", "missing_item_ids": missing})

                    db.execute(delete(MemberRestrictions).where(MemberRestrictions.member_id == member_id))
                    if new_ids:
                        db.add_all([MemberRestrictions(member_id=member_id, item_id=i) for i in sorted(new_ids)])

            # dislike_tags: None=변경없음 / ""=비우기 / 텍스트=업데이트
            if payload.dislike_tags is not None:

                if len(payload.dislike_tags) == 0:
                    # []면 dislike row 삭제(있을 때만)
                    db.execute(delete(Dislike).where(Dislike.member_id == member_id))

                tag_json = json.dumps(payload.dislike_tags, ensure_ascii=False)

                c = db.execute(
                    select(Dislike).where(Dislike.member_id == member_id)
                ).scalar_one_or_none()
                if c:
                    c.dislike_tag = json.dumps(tag_json, ensure_ascii=False)
                else:
                    db.add(Dislike(member_id=member_id, dislike_tag=tag_json))

        # 현재 재조회 아닌 입력받은 payload 사용으로 재조회 로직 사용 x

        # ---- 응답 만들기 (최신값 재조회) ----
        # item_ids = db.execute(
        #     select(MemberRestrictions.item_id).where(MemberRestrictions.member_id == member_id)
        # ).scalars().all()
        #
        # comment_raw = db.execute(
        #     select(Comment.comment_content).where(Comment.member_id == member_id)
        # ).scalar_one_or_none()
        #
        # comment_content = None
        # if comment_raw is not None:
        #     # Text 컬럼이므로 JSON 문자열 -> List[str]
        #     try:
        #         comment_content = json.loads(comment_raw)
        #     except Exception:
        #         comment_content = [comment_raw]

        return m

    except IntegrityError:
        raise HTTPException(409, detail="duplicate key")


# 삭제
def delete_member(db: Session, member_id: int) -> None:
    with db.begin():
        m = db.get(Member, member_id)
        if not m:
            raise HTTPException(status_code=404, detail="Member not found")

        # schema delete 옵션 미 설정시 아래 로직 사용!

        # # 1) member_restrictions 삭제
        # db.execute(
        #     delete(MemberRestrictions).where(MemberRestrictions.member_id == member_id)
        # )
        #
        # # 2) comment 삭제
        # db.execute(
        #     delete(Comment).where(Comment.member_id == member_id)
        # )
        #
        # # 3) member 삭제

        db.delete(m)


# NickName 체크 로직 // True / False
def is_nickname_available(db: Session, nickname: str) -> bool:

    exists = db.execute(
        select(Member.member_id).where(Member.nickname == nickname)
    ).scalar_one_or_none()

    return exists is None