import os, json
import pandas as pd
from tqdm import tqdm
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

ENDPOINT = AZURE_OPENAI_ENDPOINT
API_KEY = AZURE_OPENAI_API_KEY
API_VERSION = AZURE_OPENAI_API_VERSION
CHAT_DEPLOY = AZURE_OPENAI_DEPLOYMENT
EMBED_DEPLOY = os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT")  # 任意

client = AzureOpenAI(azure_endpoint=ENDPOINT, api_key=API_KEY, api_version=API_VERSION)

# 入出力
IN_CSV  = "trouble_db.csv"
OUT_CSV = "trouble_db_enriched.csv"

df = pd.read_csv(IN_CSV)

SYS = """あなたは製造・印刷・IT運用のトラブル記録を整えるアシスタントです。
出力は必ずJSON。フィールドは:
- normalized_tags: 日本語のタグを正規化しカンマ区切り (最大5個)
- summary_ja: 原因と対策を1~2文で簡潔に要約（日本語）
- severity_pred: 1~5の整数（5が最も重大）
- leadtime_bucket: "～8h","8-24h","24-72h","72h+"
ルール:
- 入力のseverityがあれば尊重しつつ、記述から判断して微調整可
- 正規化タグは重複・表記ゆれを統合（例: 色ムラ/色ブレ→「色」）
"""

def make_user_prompt(row: dict) -> str:
    return (
        "以下のトラブル記録を正規化・要約してください。\n"
        f"id: {row['id']}\n"
        f"date: {row['date']}\n"
        f"title: {row['title']}\n"
        f"summary: {row['summary']}\n"
        f"root_cause: {row['root_cause']}\n"
        f"countermeasure: {row['countermeasure']}\n"
        f"product: {row['product']}, client: {row['client']}\n"
        f"tags: {row['tags']}\n"
        f"severity: {row['severity']}\n"
        f"lead_time_hours: {row['lead_time_hours']}\n"
        f"tacit_notes: {row['tacit_notes']}\n"
        "JSONだけを返してください。"
    )

def call_llm(prompt: str) -> dict:
    resp = client.responses.create(
        model=CHAT_DEPLOY,
        input=[{"role": "system", "content": SYS},
               {"role": "user", "content": prompt}],
        temperature=1.0,
    )
    text = resp.output_text  # SDK 1.x のユーティリティ
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # フォールバック：コードブロック等のノイズを除去
        text = text.strip().strip("`").replace("json", "", 1)
        return json.loads(text)

def bucketize(hours: float) -> str:
    try:
        h = float(hours)
    except Exception:
        return "N/A"
    if h <= 8: return "～8h"
    if h <= 24: return "8-24h"
    if h <= 72: return "24-72h"
    return "72h+"

enriched = []
for _, row in tqdm(df.iterrows(), total=len(df)):
    row = row.to_dict()
    # 先にバケット（モデルが出し損ねた場合の保険）
    row["leadtime_bucket_calc"] = bucketize(row.get("lead_time_hours", 0))
    out = call_llm(make_user_prompt(row))

    row["normalized_tags"] = out.get("normalized_tags", "")
    row["summary_ja"]      = out.get("summary_ja", "")
    row["severity_pred"]   = out.get("severity_pred", row.get("severity"))
    row["leadtime_bucket"] = out.get("leadtime_bucket", row["leadtime_bucket_calc"])

    # （任意）埋め込みベクトルを作る場合
    if EMBED_DEPLOY:
        try:
            emb = client.embeddings.create(model=EMBED_DEPLOY, input=row["summary_ja"])
            row["embedding_dim"] = len(emb.data[0].embedding)
        except Exception:
            row["embedding_dim"] = None

    enriched.append(row)

pd.DataFrame(enriched).to_csv(OUT_CSV, index=False, encoding="utf-8")
print(f"Saved -> {OUT_CSV}")
