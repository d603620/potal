from typing import Any, Dict, List, cast

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import json
import time
from pathlib import Path

import fitz  # PyMuPDF

from app.core.chatpod_core import (
    SESSIONS,
    build_messages_for_model,
    AZURE_ENDPOINT,
    AZURE_DEPLOYMENT,
    AZURE_API_VERSION,
    AZURE_CREDENTIAL,
    AZURE_SCOPE,
)



# ===== Entra ID トークン取得（簡易キャッシュ） =====
_token_cache = {"token": None, "exp": 0}


def get_bearer_token() -> str:
    now = int(time.time())
    token = cast(str | None, _token_cache["token"])
    exp = cast(int, _token_cache["exp"])
    # 余裕を見て 60 秒前に更新
    if token and now < (exp - 60):
        return token

    access = AZURE_CREDENTIAL.get_token(AZURE_SCOPE)
    _token_cache["token"] = access.token
    _token_cache["exp"] = int(access.expires_on)
    return access.token
router = APIRouter(
    prefix="/api",        # /api/chat, /api/session など
    tags=["chatpod"],
)


# ==========
# ヘルパー
# ==========

def extract_text_from_pdf_pymupdf(raw: bytes) -> str:
    """
    PyMuPDF (fitz) を使って PDF のテキストを抽出する。
    日本語でも比較的安定して抽出できる。
    """
    texts: List[str] = []

    with fitz.open(stream=raw, filetype="pdf") as doc:
        for page in doc:
            try:
                # get_text の戻り値は型定義上 Union なので、str として明示的に cast する
                raw_text = page.get_text("text")
                page_text = cast(str, raw_text)
            except Exception:
                page_text = ""
            if page_text:
                texts.append(page_text)

    return "\n\n".join(texts)


def extract_text_from_upload(filename: str, raw: bytes) -> str:
    """
    アップロードファイルからテキストを抽出する。
    - .pdf は PyMuPDF で解析
    - それ以外は UTF-8 デコード（読めない部分は無視）
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        try:
            return extract_text_from_pdf_pymupdf(raw)
        except Exception:
            # PDF パースに失敗した場合でも、最後の手段として生テキストを返す
            fallback = raw.decode("utf-8", errors="ignore")
            return (
                "[PyMuPDF で PDF 抽出に失敗したため、バイナリを UTF-8 として解釈した結果です]\n"
                + fallback
            )

    # テキストファイルなどは素直に UTF-8 として読む
    return raw.decode("utf-8", errors="ignore")


# ==========
# API 定義
# ==========


@router.options("/chat")
async def options_chat():
    # CORS のプレフライト用
    return Response(status_code=204)


@router.get("/healthz")
async def health():
    return {"ok": True}


@router.post("/session")
async def create_session():
    import uuid

    sid = uuid.uuid4().hex
    SESSIONS[sid]  # 初期化だけしておく
    return {"session_id": sid}


@router.post("/upload")
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    ファイルアップロード用 API。

    - フロントから送られた session_id / file を受け取る
    - PDF は PyMuPDF でテキスト抽出、それ以外は UTF-8 デコード
    - 抽出テキストを SESSIONS[session_id] に user メッセージとして自動追記
      → 以後の /chat 呼び出しでは、この内容が「裏のコンテキスト」として使われる
    - フロントにはプレビュー情報のみ返す
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=400, detail="invalid session_id")

    try:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="empty file")

        # 1) 拡張子に応じたテキスト抽出（PDF は PyMuPDF）
        safe_filename = file.filename or "uploaded_file"
        full_text = extract_text_from_upload(safe_filename, raw)

        # 2) モデルに渡すコンテキスト量を制限（長い PDF 対策）
        MAX_CONTEXT_CHARS = 20000
        context_text = full_text[:MAX_CONTEXT_CHARS]

        # 3) サーバ側会話履歴に「ユーザーがファイルを与えた」という形で追加
        hist = SESSIONS[session_id]
        hist.append(
            {
                "role": "user",
                "content": (
                    f"以下はユーザーがアップロードしたファイル「{safe_filename}」の内容です。\n"
                    f"以後の質問に回答する際は、この内容を前提として参照してください。\n\n"
                    f"{context_text}"
                ),
            }
        )

        # 4) フロントにはプレビューだけ返す（全文は返さない）
        PREVIEW_CHARS = 400
        preview = full_text[:PREVIEW_CHARS]

        return {
            "filename": safe_filename,
            "preview": preview,
            "chars_total": len(full_text),
            "chars_used_in_context": len(context_text),
        }


    except HTTPException:
        # 上で raise したものはそのまま流す
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"upload failed: {e}")


@router.post("/chat")
async def chat_route(payload: Dict[str, Any], request: Request):
    """
    ストリーミング用チャットAPI（SSE）
    2通りの呼び出しをサポート：
      A) { session_id: string, user_text: string }
      B) { messages: ChatMessage[] }  ※互換用
    """
    session_id: str | None = payload.get("session_id")
    user_text: str | None = payload.get("user_text")

    if session_id and user_text:
        # サーバ側にある履歴をもとに messages を構築
        hist = SESSIONS[session_id]
        outbound_messages = build_messages_for_model(hist, user_text)
    else:
        outbound_messages: List[Dict[str, Any]] = payload.get("messages", [])
        if not isinstance(outbound_messages, list) or not outbound_messages:
            raise HTTPException(
                status_code=400,
                detail="messages or (session_id & user_text) required",
            )

    #url = f"{AZURE_ENDPOINT}/openai/v1/chat/completions"
    url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_bearer_token()}",
    }
    body = {
        "model": AZURE_DEPLOYMENT,   # デプロイ名
        "messages": outbound_messages,
        "stream": True,
    }

    async def event_stream():
        timeout = httpx.Timeout(None)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, headers=headers, json=body) as upstream:
                    print(
                        "upstream:",
                        upstream.status_code,
                        upstream.headers.get("content-type"),
                    )

                    if upstream.status_code >= 400:
                        text = await upstream.aread()
                        err = {"error": text.decode("utf-8", "ignore")}
                        # エラーも SSE でフロントに送って終端
                        yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode(
                            "utf-8"
                        )
                        yield b"data: [DONE]\n\n"
                        return

                    assistant_text_parts: List[str] = []
                    first = True
                    try:
                        async for chunk in upstream.aiter_raw():
                            if not chunk:
                                continue
                            if first:
                                print("<< first SSE chunk >>", chunk[:200])
                                first = False

                            # delta.content を取り出して保存（ざっくりパーサ）
                            try:
                                for line in chunk.split(b"\n\n"):
                                    if not line.startswith(b"data:"):
                                        continue
                                    data = line[5:].strip()
                                    if data == b"[DONE]":
                                        continue
                                    j = json.loads(data)
                                    delta = (
                                        j.get("choices", [{}])[0]
                                        .get("delta", {})
                                        .get("content")
                                    )
                                    if delta:
                                        assistant_text_parts.append(delta)
                            except Exception:
                                # パース失敗は無視（そのままフロントに転送）
                                pass

                            # クライアントには元の SSE をそのまま転送
                            yield chunk

                        # 念のため終端マーカー
                        yield b"data: [DONE]\n\n"

                    finally:
                        # セッションを使って呼ばれた場合のみサーバ側履歴を更新
                        if session_id and (user_text is not None):
                            hist = SESSIONS[session_id]
                            hist.append({"role": "user", "content": user_text})
                            hist.append(
                                {
                                    "role": "assistant",
                                    "content": "".join(assistant_text_parts),
                                }
                            )

        except httpx.TimeoutException:
            err = {"error": "Upstream timeout"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode(
                "utf-8"
            )
            yield b"data: [DONE]\n\n"
        except httpx.HTTPError as e:
            err = {"error": f"Upstream connection error: {e}"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode(
                "utf-8"
            )
            yield b"data: [DONE]\n\n"
        except Exception as e:
            err = {"error": f"Internal error: {e}"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode(
                "utf-8"
            )
            yield b"data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat-test")
async def chat_test(payload: Dict[str, Any]):
    """
    Azure OpenAI への疎通確認用API（ストリームなし）
    """
    messages: List[Dict[str, Any]] = payload.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    #url = f"{AZURE_ENDPOINT}/openai/v1/chat/completions"
    url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_bearer_token()}",
    }
    body = {
        "model": AZURE_DEPLOYMENT,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            r = await client.post(url, headers=headers, json=body)

        # Azure からのレスポンスをできるだけそのまま返す
        try:
            data = r.json()
        except ValueError:
            data = {"raw": r.text}

        return JSONResponse(status_code=r.status_code, content=data)

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"test call failed: {e}")
