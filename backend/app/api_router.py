from fastapi import APIRouter

from .features.member.router import router as member_router
from .features.review.router import router as review_router
from .features.community.router import router as community_router
from .features.restrictions.router import router as restrictions_router

# router 미작업
# from .features.auth.router import router as auth_router

# router 전체 관리
api_router = APIRouter()

api_router.include_router(member_router)
api_router.include_router(review_router)
api_router.include_router(community_router)
api_router.include_router(restrictions_router)

# router 미작업
# api_router.include_router(auth_router)
