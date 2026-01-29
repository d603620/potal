# backend/app/routers/auth.py

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.auth import login
from app.core.security import SECRET_KEY, ALGORITHM

from app.core.auth import login, get_user_by_employee_id

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------- ログイン用リクエスト／レスポンス ----------

class LoginRequest(BaseModel):
    employee_id: str
    password: str


class User(BaseModel):
    employee_id: str
    name: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    user: User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login", response_model=LoginResponse)
def login_api(body: LoginRequest):
    """
    ログインAPI
    - 成功: JWTトークン＋ユーザ情報を返す
    - 失敗: 401
    """
    result = login(body.employee_id, body.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # core.auth.login から返ってきた dict を User に詰め直す
    user_dict = result["user"]
    user = User(
        employee_id=user_dict.get("employee_id"),
        name=user_dict.get("name"),
    )

    return {
        "token": result["token"],
        "user": user,
    }


# ---------- API側で使う共通の認証依存関数 ----------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Authorization: Bearer <token> を受け取り、
    JWTを検証してUser情報を返す依存関数。
    app.routers.api などから Depends(get_current_user) で利用。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_id: Optional[str] = payload.get("sub")
        if employee_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 本来はここでDBからユーザ情報を取得する。
    # いったんはIDだけ入れたUserを返す。
#    return User(employee_id=employee_id, name=None)
    user_dict = get_user_by_employee_id(employee_id)
    if not user_dict:
        raise credentials_exception

    return User(
        employee_id=user_dict["employee_id"],
        name=user_dict["name"],
    )