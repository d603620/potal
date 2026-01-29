from fastapi import APIRouter
from urllib.parse import quote  # URLエンコード用

router = APIRouter()

API_BASE = "http://localhost:8000"  # 必要に応じて変更


def with_file_url(item: dict) -> dict:
    """
    file_name がある場合は file_url を追加する。
    """
    if "file_name" in item:
        encoded = quote(item["file_name"])
        item["file_url"] = f"/api/data/{encoded}"
    return item


SCENARIO = [
    with_file_url({
        "role": "user",
        "text": (
            "下請法が改正されて取引法になりました。\n"
            "下記の公正取引委員会のガイドブックから\n"
            "URL:https://www.jftc.go.jp/file/toriteki002.pdf\n"
            "発注担当者に周知するための1時間の勉強会での説明資料とQ&Aをつくって。"
        ),
    }),
    with_file_url({
        "role": "assistant",
        "text": "承知しました。\n10ページの教育資料とQ&Aを作成します。",
    }),
    with_file_url({
        "role": "assistant",
        "text": "教育資料です。内容をご確認ください。",
        "file_name": "取適法改正ガイドライン講義.pptx",
    }),
    with_file_url({
        "role": "user",
        "text": "ありがとう。\nメールでの案内用に、2ページの短縮版もつくってくれるかな。",
    }),
    with_file_url({
        "role": "assistant",
        "text": "もちろんです。2ページの短縮版の資料です。",
        "file_name": "法改正勉強会案内_ショート版.pptx",
    }),
    with_file_url({
        "role": "assistant",
        "text": (
            "外注発注マニュアルにも変更点を反映させますか？\n"
            "関連するマニュアルは下記です。"
        ),
        "file_name": "QMS-8.4-WI-012 Rev.3（外部提供者管理手順）.docx",
    }),
    with_file_url({
        "role": "user",
        "text": "ありがとう。変更点を反映させて",
    }),
    with_file_url({
        "role": "assistant",
        "text": "変更点を反映させました。",
    }),
]


@router.get("/scenario")
async def get_scenario():
    return {"scenario": SCENARIO}
