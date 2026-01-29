from fastapi import APIRouter, Header, HTTPException
from app.routers.auth import get_current_user, User

router = APIRouter()

@router.get("/hello")
def hello():
  return {"message": "ようこそ！React + FastAPI ポータルのサンプルです。"}

@router.get("/me")
async def me(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]

    user: User = await get_current_user(token)
    return {"employee_id": user.employee_id, "name": user.name}
   