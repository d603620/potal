from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.178.7.4:5173",
    ]

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"


settings = Settings()
