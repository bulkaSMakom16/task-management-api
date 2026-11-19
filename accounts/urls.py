from fastapi import APIRouter

from .schemas import TokenRead, UserRead
from .views import login_user, register_user


router = APIRouter(prefix="/api/auth", tags=["auth"])

router.add_api_route(
    "/register/",
    register_user,
    methods=["POST"],
    status_code=201,
    response_model=UserRead,
)
router.add_api_route("/login/", login_user, methods=["POST"], response_model=TokenRead)
