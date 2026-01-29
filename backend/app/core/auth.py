# backend/app/core/auth.py
from passlib.context import CryptContext
from app.core.security import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ★今はダミー。実際はDBから社員情報を取得する想定
_dummy_user = {
  "employee_id": "Deng1",
  "hashed_password": pwd_context.hash("dengdeng123!!"),
  "name": "革新研データエンジニアリング開発部-Giiji",
}

def authenticate_user(employee_id: str, password: str) -> dict | None:
  """
  社員IDとパスワードを検証し、OKならユーザ情報を返す
  """
  if employee_id != _dummy_user["employee_id"]:
    return None

  if not pwd_context.verify(password, _dummy_user["hashed_password"]):
    return None

  # 必要な情報だけ返却
  return {
    "employee_id": _dummy_user["employee_id"],
    "name": _dummy_user["name"],
  }

def login(employee_id: str, password: str) -> dict | None:
  """
  認証し、OKならトークンとユーザ情報を返す
  """
  user = authenticate_user(employee_id, password)
  if not user:
    return None

  token = create_access_token({"sub": user["employee_id"]})
  return {
    "token": token,
    "user": user,
  }

def get_user_by_employee_id(employee_id: str) -> dict | None:
  if employee_id != _dummy_user["employee_id"]:
    return None

  return {
    "employee_id": _dummy_user["employee_id"],
    "name": _dummy_user["name"],
  }