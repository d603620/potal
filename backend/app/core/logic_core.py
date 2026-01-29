import io, os, json, difflib, hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, cast
import io
from fastapi import HTTPException, UploadFile

# ==== パス設定 ====
HERE = Path(__file__).resolve().parent.parent
# print(f"[DEBUG] logic_core HERE: {HERE}")   
ROOT = HERE.parents[2] if (HERE.name == "services") else Path.cwd()
TREE_PATH = ROOT / "tree.txt"
SYSTEM_PROMPT_PATH = ROOT / "system_prompt.txt"
HITEI_SAVE_DIR = ROOT / "data" / "hitei_files"
HITEI_SAVE_DIR.mkdir(parents=True, exist_ok=True)

# ==== 各種ファイル → テキスト抽出 ====

def _read_pdf(bio: io.BytesIO) -> str:
    """
    PyMuPDF (fitz) で PDF からテキストを抽出する。
    """
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PyMuPDF is not available: {e}")

    try:
        bio.seek(0)
        doc = fitz.open(stream=bio.read(), filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot open PDF: {e}")

    texts: list[str] = []
    for page in doc:
        if hasattr(page, "get_text"):
            raw = page.get_text("text")
            # 型: str | list | dict | None などの可能性をすべて str にそろえる
            if isinstance(raw, str):
                val = raw
            elif raw is None:
                val = ""
            else:
                val = str(raw)
            texts.append(val)
        else:
            raise TypeError(f"The object does not have a 'get_text' method: {type(page)}")

    return "\n".join(texts)


def _read_docx(bio: io.BytesIO) -> str:
    try:
        import docx
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX reader not available: {e}")
    d = docx.Document(bio)
    return "\n".join(p.text for p in d.paragraphs)

def _read_excel_or_csv(bio: io.BytesIO, ext: str) -> str:
    try:
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"pandas not available: {e}")
    bio.seek(0)
    if ext == ".csv":
        df = pd.read_csv(bio)
        return df.to_csv(index=False)
    xls = pd.ExcelFile(bio)
    blocks = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        blocks.append(f"## シート: {sheet}\n" + df.to_csv(index=False))
    return "\n\n".join(blocks)

async def extract_text_from_upload(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    raw = await upload.read()
    bio = io.BytesIO(raw)
    if name.endswith(".pdf"):
        return _read_pdf(bio)
    if name.endswith(".docx"):
        return _read_docx(bio)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return _read_excel_or_csv(bio, ".xlsx")
    if name.endswith(".csv"):
        return _read_excel_or_csv(bio, ".csv")
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

async def hitei_dedupe_and_extract(upload: UploadFile) -> Tuple[str, str]:
    text = await extract_text_from_upload(upload)
    h = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()
    uploaded_path = HITEI_SAVE_DIR / (upload.filename or f"hitei_{datetime.now().timestamp():.0f}.txt")
    for f in HITEI_SAVE_DIR.glob("*"):
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
            if hashlib.md5(t.encode("utf-8", errors="ignore")).hexdigest() == h:
                return t, f"既存ファイル（{f.name}）を再利用します。"
        except Exception:
            continue
    try:
        uploaded_path.write_text(text, encoding="utf-8", errors="ignore")
        return text, f"新規ファイル（{uploaded_path.name}）として保存しました。"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存に失敗しました: {e}")

# ==== Azure OpenAI (v1 SDK) ====
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from dnp_azure_auth.config import load_azure_openai_config
from dnp_azure_auth.credential import get_credential

load_dotenv()

def _get_env_str(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise HTTPException(status_code=500, detail=f"Environment variable '{name}' is not set.")
    return v

# Azure OpenAI config（endpoint / deployment / api_version / scope）
cfg = load_azure_openai_config(
    endpoint_env="API_AZURE_OPENAI_ENDPOINT",
    deployment_env="API_AZURE_OPENAI_DEPLOYMENT",
    api_version_env="API_AZURE_OPENAI_API_VERSION",
)

AZURE_OPENAI_ENDPOINT: str = cfg.endpoint
AZURE_OPENAI_DEPLOYMENT: str = cfg.deployment
AZURE_OPENAI_API_VERSION: str = cfg.api_version or "2024-02-01"

# Azure AD auth（dnp_azure_auth）
# mode: auto | mi | sp | cli
auth_mode = os.getenv("AZURE_AUTH_MODE", "auto")
cred = get_credential(auth_mode)

def azure_ad_token_provider() -> str:
    # Azure OpenAI 用 scope（既定: https://cognitiveservices.azure.com/.default）
    return cred.get_token(cfg.scope).token

try:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_ad_token_provider=azure_ad_token_provider,
    )
except Exception as e:
    client = None
    print(f"Azure OpenAI client initialization failed: {e}")


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        print(f"[DEBUG] system_prompt loaded: {len(text)} chars from {SYSTEM_PROMPT_PATH}")
        return text
    print("[DEBUG] system_prompt.txt not found, using default message")
    return "あなたは発注書と該非判定書からJSONを作るアシスタントです。厳密にJSONのみを返してください。"

def _build_user_prompt(po_text: str, hitei_text: str, instruction: Optional[str]) -> str:
    base = f"""### 発注書（抽出テキスト）
{po_text}

### 該非判定書（抽出テキスト）
{hitei_text}
"""
    if instruction and instruction.strip():
        base += f"\n### 修正指示\n{instruction.strip()}\n"
    base += "\n### 最終出力：JSON オブジェクトのみを返す\n"
    return base

def generate_json_draft(po_text: str, hitei_text: str, instruction: Optional[str] = None) -> dict:
    if not client:
        raise HTTPException(status_code=500, detail="Azure OpenAI client is not initialized. Check environment variables.")

    # messages の型を ChatCompletionMessageParam に合わせる
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": _build_user_prompt(po_text, hitei_text, instruction)},
    ]

    try:
        resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,   # str（None にならない）
            messages=messages,               # 正しい型
            temperature=1.0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        if content is None:
            raise HTTPException(status_code=500, detail="Azure OpenAI returned empty content.")
        return json.loads(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure OpenAI error: {e}")

# ==== JSON差分 ====
def _json_str(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True)

def unified_diff_text(old: dict, new: dict, fromfile: str = "current.json", tofile: str = "preview.json") -> str:
    old_s = _json_str(old).splitlines(False) if old else []
    new_s = _json_str(new).splitlines(False) if new else []
    diff = difflib.unified_diff(old_s, new_s, fromfile=fromfile, tofile=tofile, lineterm="")
    return "\n".join(diff) or "(差分なし)"

# ==== tree.txt ====
def load_tree_text() -> str:
    if not TREE_PATH.exists():
        return ""
    return TREE_PATH.read_text(encoding="utf-8", errors="ignore")
