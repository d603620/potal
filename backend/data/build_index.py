###############################################################
# Python3.12  FAISS Index Builder Script
# Create  2025/11/14 Nishimoto
# Need by: requirements.txt & model dependency installed
# 機能概要:
#   ・トラブル事例などのCSVを読み込み、テキストをEmbedding（ベクトル化）
#   ・FAISSインデックスを作成し、検索用に保存
#   ・日本語対応 SentenceTransformer モデルを使用
#   ・最近N年分のデータを対象に絞り込み
###############################################################

import argparse
import os
import pickle
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss

# -------------------------------------------------------------
# デフォルトで使用するテキスト列の指定
# -------------------------------------------------------------
DEFAULT_TEXT_COLS = ["title", "summary", "root_cause", "countermeasure", "tacit_notes", "summary_ja"]

# 使用モデル（日本語・多言語対応の高品質モデル）
MODEL_NAME = "intfloat/multilingual-e5-base"

# -------------------------------------------------------------
# CSV読込関数
# -------------------------------------------------------------
def load_df(path: str) -> pd.DataFrame:
    """CSVファイルを読み込み、日付列を正規化・空欄を補完"""
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")  # 日付変換（無効値はNaT）
    for col in ["tags", "product"]:
        if col in df.columns:
            df[col] = df[col].fillna("")  # 欠損を空文字で補完
    return df

# -------------------------------------------------------------
# テキスト列を連結して1件の文章にする
# -------------------------------------------------------------
def build_text_series(df: pd.DataFrame, text_cols=DEFAULT_TEXT_COLS) -> pd.Series:
    """複数列を結合してEmbedding対象のテキストを生成"""
    cols = [c for c in text_cols if c in df.columns]
    def row_text(r):
        parts = []
        for c in cols:
            val = str(r.get(c, "") or "").strip()
            if val:
                parts.append(val)
        return " \n".join(parts)
    return df.apply(row_text, axis=1)

# -------------------------------------------------------------
# テキストをベクトル化（Embedding）
# -------------------------------------------------------------
def embed_corpus(texts, model_name=MODEL_NAME, batch_size=128):
    """SentenceTransformerで文章をEmbedding"""
    model = SentenceTransformer(model_name)
    # E5モデルでは「passage:」を前置する必要がある
    passages = [f"passage: {t}" for t in texts]
    embs = model.encode(passages, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
    return embs.astype("float32")

# -------------------------------------------------------------
# FAISS Indexの構築
# -------------------------------------------------------------
def build_faiss_index(embeddings: np.ndarray):
    """内積ベース（コサイン類似度）FAISS Indexを構築"""
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)  # 内積法
    index.add(embeddings)  # type: ignore[call-arg]
    return index

# -------------------------------------------------------------
# メイン処理
# -------------------------------------------------------------
def main():
    """CLIで実行されるメイン処理"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="入力CSVファイルパス")
    ap.add_argument("--index_dir", required=True, help="インデックス出力ディレクトリ")
    ap.add_argument("--years", type=int, default=10, help="取り込む過去年数（デフォルト10年）")
    ap.add_argument("--text_cols", nargs="*", default=DEFAULT_TEXT_COLS, help="使用するテキスト列")
    args = ap.parse_args()

    # 出力先ディレクトリを作成
    os.makedirs(args.index_dir, exist_ok=True)

    # --- データ読込 ---
    df = load_df(args.data)

    # --- 年数フィルタリング ---
    cutoff = pd.Timestamp(datetime.now() - timedelta(days=365 * args.years))
    df = df[df["date"] >= cutoff].reset_index(drop=True)

    # --- Embedding作成 ---
    texts = build_text_series(df, args.text_cols)
    embs = embed_corpus(texts)

    # --- FAISS Index構築 ---
    index = build_faiss_index(embs)

    # --- 保存処理 ---
    faiss.write_index(index, os.path.join(args.index_dir, "trouble.faiss"))
    df.to_parquet(os.path.join(args.index_dir, "metadata.parquet"), index=False)

    # モデル名・列情報などを設定ファイルとして保存
    with open(os.path.join(args.index_dir, "config.pkl"), "wb") as f:
        pickle.dump({
            "model_name": MODEL_NAME,
            "text_cols": args.text_cols,
        }, f)

    print(f"Indexed {len(df)} records into {args.index_dir}")

# -------------------------------------------------------------
# スクリプト単体実行時のエントリーポイント
# -------------------------------------------------------------
if __name__ == "__main__":
    main()
