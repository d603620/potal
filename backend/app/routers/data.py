# app/routers/data.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import mimetypes

router = APIRouter()

# backend/app/routers/data.py から見て 3つ上が backend ルート想定
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


@router.get("/data/{file_name}")
async def download_data(file_name: str):
    # パスを悪用されないようにファイル名部分だけ取り出す
    safe_name = Path(file_name).name
    file_path = DATA_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=mime or "application/octet-stream",
    )
