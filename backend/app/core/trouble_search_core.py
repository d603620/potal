"""
トラブルDB類似検索コアロジック

- FAISS によるベクトル検索
- TF-IDF による再ランク
- メタ情報に基づくフィルタ
- フィードバック / 暗黙知 CSV への書き込み
- 分析用の簡易統計値計算

※ このモジュールには Web フレームワーク（FastAPI / Streamlit）への依存を持たせない。
  → API や UI からは、このモジュールの関数だけを呼び出す想定。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import datetime as dt
import json

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# faiss / sentence-transformers は import エラーになる可能性があるので必要に応じてエラーハンドリング
try:
    import faiss  # type: ignore
except Exception as e:  # pragma: no cover
    faiss = None  # 実行時にチェックする

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception as e:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


# =========================
# データクラス定義
# =========================

@dataclass
class TroubleSearchConfig:
    model_name: str
    text_cols: List[str]
    id_col: str = "id"
    date_col: str = "date"
#    severity_col: str = "severity"
    severity_col: str = "severity_pred"
    product_col: str = "product"
    tags_col: str = "tags"


@dataclass
class TroubleSearchResources:
    index_dir: Path
    faiss_index: Any
    meta: pd.DataFrame
    config: TroubleSearchConfig
    model: Any
    tfidf_vectorizer: TfidfVectorizer
    tfidf_corpus: Any  # sparse matrix


# =========================
# ロード系
# =========================

def _load_config(config_path: Path) -> TroubleSearchConfig:
    """8_truble_ai.py の config.pkl 相当を読み込む想定。

    プロジェクト側でフォーマットを変える場合は、ここを書き換える。
    """
    import pickle

    with config_path.open("rb") as f:
        raw = pickle.load(f)

    # 8_truble_ai.py の config を想定（例: {"model_name": "...", "text_cols": [...]}）
    return TroubleSearchConfig(
        model_name=raw.get("model_name", "sentence-transformers/intfloat/multilingual-e5-large"),
        text_cols=list(raw.get("text_cols", [])),
        id_col=raw.get("id_col", "id"),
        date_col=raw.get("date_col", "date"),
        severity_col=raw.get("severity_col", "severity_pred"),
        product_col=raw.get("product_col", "product"),
        tags_col=raw.get("tags_col", "tags"),
    )


def _build_tfidf(meta: pd.DataFrame, config: TroubleSearchConfig) -> Tuple[TfidfVectorizer, Any]:
    """メタ情報から TF-IDF コーパスを作成する。"""
    texts: List[str] = []

    for _, row in meta.iterrows():
        parts: List[str] = []
        for col in config.text_cols:
            val = row.get(col)
            if isinstance(val, str):
                parts.append(val)
        joined = " ".join(parts)
        texts.append(joined)

    vectorizer = TfidfVectorizer()
    tfidf_corpus = vectorizer.fit_transform(texts)
    return vectorizer, tfidf_corpus


@lru_cache(maxsize=1)
def load_resources(index_dir: str | Path) -> TroubleSearchResources:
    """
    トラブル検索で使用するリソースを全てロードし、キャッシュする。

    Parameters
    ----------
    index_dir : str | Path
        trouble.faiss / metadata.parquet / config.pkl が置かれているディレクトリ

    Returns
    -------
    TroubleSearchResources
    """
    index_dir = Path(index_dir)

    # --- config ---
    config_path = index_dir / "config.pkl"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    config = _load_config(config_path)

    # --- metadata ---
    meta_path = index_dir / "metadata.parquet"
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata not found: {meta_path}")
    meta = pd.read_parquet(meta_path)

    meta = meta.reset_index(drop=True)
    
    # --- FAISS index ---
    if faiss is None:
        raise RuntimeError("faiss がインポートできません。ライブラリのインストールを確認してください。")
    index_path = index_dir / "trouble.faiss"
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    faiss_index = faiss.read_index(str(index_path))

    # --- SentenceTransformer model ---
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers がインポートできません。ライブラリのインストールを確認してください。")
    model = SentenceTransformer(config.model_name)

    # --- TF-IDF ---
    tfidf_vectorizer, tfidf_corpus = _build_tfidf(meta, config)
 
    return TroubleSearchResources(
        index_dir=index_dir,
        faiss_index=faiss_index,
        meta=meta,
        config=config,
        model=model,
        tfidf_vectorizer=tfidf_vectorizer,
        tfidf_corpus=tfidf_corpus,
    )

# =========================
# 埋め込み & 検索
# =========================

def encode_query(resources: TroubleSearchResources, query: str) -> np.ndarray:
    """クエリを E5 形式でエンコードしてベクトルに変換する。"""
    prefix = "query: "
    emb = resources.model.encode(prefix + query, normalize_embeddings=True)
    if emb.ndim == 1:
        emb = emb.reshape(1, -1)
    return emb.astype("float32")


def vector_search(
    resources: TroubleSearchResources,
    query_vec: np.ndarray,
    top_k: int = 20,
) -> Tuple[np.ndarray, np.ndarray]:
    """FAISS でベクトル検索を行い、(scores, indices) を返す。"""
    index = resources.faiss_index
    distances, indices = index.search(query_vec, top_k)  # L2 距離
    # 類似度に変換（小さいほど近い → -distance にするなど）
    scores = -distances
    return scores[0], indices[0]


def tfidf_rerank(
    resources: TroubleSearchResources,
    query: str,
    candidate_indices: Sequence[int],
    alpha: float = 0.5,
    faiss_scores: Optional[Sequence[float]] = None,
) -> List[int]:
    """
    TF-IDF による再ランク処理。

    Parameters
    ----------
    alpha : float
        0〜1。1 に近いほど TF-IDF の比重が高い。
    """
    tfidf = resources.tfidf_vectorizer
    corpus = resources.tfidf_corpus

    q_vec = tfidf.transform([query])
    cand_matrix = corpus[list(candidate_indices)]
    q_vec_t = q_vec.transpose() # type: ignore
    tfidf_scores = (cand_matrix @ q_vec_t).toarray().ravel()

    if faiss_scores is None:
        combined = tfidf_scores
    else:
        # ★ ここだけ修正：別名の numpy 配列を使う
        faiss_scores_arr = np.asarray(faiss_scores, dtype="float32")

        # スコアを0-1にスケーリング（簡易版）
        def _minmax(x: np.ndarray) -> np.ndarray:
            if x.size == 0:
                return x
            xmin, xmax = x.min(), x.max()
            if xmax - xmin < 1e-9:
                return np.zeros_like(x)
            return (x - xmin) / (xmax - xmin)

        faiss_norm = _minmax(faiss_scores_arr)
        tfidf_norm = _minmax(tfidf_scores)
        combined = (1 - alpha) * faiss_norm + alpha * tfidf_norm

    order = np.argsort(combined)[::-1]
    reranked_indices = [int(candidate_indices[i]) for i in order]
    return reranked_indices


# =========================
# フィルタリング
# =========================

def _to_datetime(x: Any) -> Optional[dt.date]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if isinstance(x, dt.date):
        return x
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return dt.datetime.strptime(x, fmt).date()
            except Exception:
                continue
    return None


def _parse_severity(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        # 文字列ラベル -> 数値にマップする場合はここで定義
        mapping = {
            "低": 1.0,
            "中": 2.0,
            "高": 3.0,
            "critical": 4.0,
            "重大": 5.0,
        }
        if s in mapping:
            return mapping[s]
        try:
            return float(s)
        except Exception:
            return None
    return None


def filter_meta(
    resources: TroubleSearchResources,
    years: Optional[int] = None,
    severity_min: Optional[float] = None,
    severity_max: Optional[float] = None,
    products: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
) -> pd.Index:
    """
    メタ情報に対して、年数 / 重大度 / 製品 / タグ のフィルタをかけ、残った行の index を返す。
    """
    meta = resources.meta
    cfg = resources.config

    mask = pd.Series(True, index=meta.index)

    # 年数フィルタ（直近 N 年）
    if years is not None and years > 0: 
        today = dt.date.today()
        threshold = today - dt.timedelta(days=365 * years)

        # pandas 側に合わせて Timestamp にそろえる
        dates = pd.to_datetime(meta[cfg.date_col], errors="coerce")
        threshold_ts = pd.Timestamp(threshold)

        # NaT を除外しつつ、Timestamp >= Timestamp で比較
        mask &= (dates.notna()) & (dates >= threshold_ts)

    # 重大度フィルタ
    if severity_min is not None or severity_max is not None:
        # まずは _parse_severity で数値化を試みる
        sev_vals = meta[cfg.severity_col].map(_parse_severity)

        # pandas の数値 Series にして、変換できないものは NaN にする
        sev_series = pd.to_numeric(sev_vals, errors="coerce")

        # ★ ポイント：
        #    ・NaN（= 重大度不明）はフィルタで「落とさない」
        #    ・指定された範囲にだけ厳密に絞る
        if severity_min is not None:
            mask &= (sev_series.isna() | (sev_series >= severity_min))
        if severity_max is not None:
            mask &= (sev_series.isna() | (sev_series <= severity_max))

    # product フィルタ
    if products:
        prod_set = set(products)

        def _match_product(v: Any) -> bool:
            if v is None:
                return False
            if isinstance(v, str):
                return v in prod_set
            return False

        mask &= meta[cfg.product_col].map(_match_product)

    # tags フィルタ（「, 区切り文字列」や「リスト」などを想定）
    if tags:
        tag_set = set(tags)

        def _match_tags(v: Any) -> bool:
            if v is None:
                return False
            if isinstance(v, str):
                parts = [s.strip() for s in v.split(",") if s.strip()]
            elif isinstance(v, (list, tuple, set)):
                parts = [str(x).strip() for x in v]
            else:
                return False
            return any(p in tag_set for p in parts)

        mask &= meta[cfg.tags_col].map(_match_tags)

    return meta[mask].index


# =========================
# 検索 API 向けのラッパ
# =========================

def search_cases(
    index_dir: str | Path,
    query: str,
    *,
    years: Optional[int] = None,
    severity_min: Optional[float] = None,
    severity_max: Optional[float] = None,
    products: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
    top_k: int = 30,
    alpha: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    一発で「フィルタ → ベクトル検索 → TF-IDF 再ランク → 結果整形」まで行うヘルパ。

    FastAPI などからは、基本的にこの関数だけ呼べばよい想定。
    """
    resources = load_resources(index_dir)

    # 1. メタにフィルタをかける
    candidate_idx = filter_meta(
        resources,
        years=years,
        severity_min=severity_min,
        severity_max=severity_max,
        products=products,
        tags=tags,
    )
    if len(candidate_idx) == 0:
        return []

    # 2. クエリをエンコードして FAISS 検索
    q_vec = encode_query(resources, query)
    # FAISS の Index は全件対象なので、いったん全体で top_k を取る
    faiss_scores, faiss_indices = vector_search(resources, q_vec, top_k=top_k)
    # ★ ここにデバッグ出力を追加
    #print("DEBUG len(meta)        :", len(resources.meta))
    #print("DEBUG candidate_idx[:10]:", list(candidate_idx[:10]))
    #print("DEBUG faiss_indices[:10]:", list(faiss_indices[:10]))

    # 3. フィルタ後の index に限定
    #    → faiss_indices（0..N-1）と meta.index（任意）を対応させるため、
    #      8_truble_ai.py では「pos -> meta index」の対応があるはず。
    #    ここでは簡易に「faiss の行順 = meta の行順」と仮定するので、
    #    実データ構造に応じて調整が必要な場合はここを修正する。
    faiss_indices = np.asarray(faiss_indices, dtype=int)
    faiss_scores = np.asarray(faiss_scores, dtype="float32")

    # 候補のうちフィルタに通ったものだけ抜き出す
    candidate_set = set(candidate_idx.tolist())
    filtered_positions: List[int] = []
    filtered_scores: List[float] = []
    for pos, score in zip(faiss_indices, faiss_scores):
        if pos in candidate_set:
            filtered_positions.append(pos)
            filtered_scores.append(float(score))

    if not filtered_positions:
        return []

    # 4. TF-IDF 再ランク
    reranked = tfidf_rerank(
        resources,
        query=query,
        candidate_indices=filtered_positions,
        alpha=alpha,
        faiss_scores=filtered_scores,
    )

    # 5. 結果整形（そのまま JSON 返却できる dict にする）
    meta = resources.meta
    cfg = resources.config

    results: List[Dict[str, Any]] = []
    for idx in reranked:
        row = meta.loc[idx]
        item: Dict[str, Any] = {
            "internal_index": int(idx),
            cfg.id_col: row.get(cfg.id_col),
        }
        for col in meta.columns:
            val = row.get(col)
            # date / datetime は文字列に変換
            if isinstance(val, (dt.date, dt.datetime)):
                val = val.isoformat()
            # ★ NumPy スカラーは Python の素の型に変換
            if isinstance(val, np.generic):
                val = val.item()
            item[col] = val
        results.append(item)

    return results


# =========================
# フィードバック / 暗黙知
# =========================

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def record_feedback(
    csv_path: str | Path,
    *,
    query: str,
    case_id: Any,
    helpful: bool,
    solve_hours: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    検索結果に対するフィードバックを CSV に追記する。

    8_truble_ai.py の search_feedback.csv に相当。
    """
    csv_path = Path(csv_path)
    _ensure_parent(csv_path)

    record: Dict[str, Any] = {
        "timestamp": dt.datetime.now().isoformat(),
        "query": query,
        "case_id": case_id,
        "helpful": helpful,
        "solve_hours": solve_hours,
    }
    if extra:
        for k, v in extra.items():
            # 重複キーは extra を優先
            record[k] = v

    df_new = pd.DataFrame([record])

    if csv_path.exists():
        df_old = pd.read_csv(csv_path)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_csv(csv_path, index=False)


def append_tacit_knowledge(
    csv_path: str | Path,
    *,
    case_id: Any,
    note: str,
    category: Optional[str] = None,
    status: str = "pending",
    author: Optional[str] = None,
    approver: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    暗黙知を CSV に追記する。

    8_truble_ai.py の tacit_knowledge.csv に相当。
    """
    csv_path = Path(csv_path)
    _ensure_parent(csv_path)

    # ------------------------------------------------------------
    # 重要: tacit_knowledge.csv は「承認/却下」の参照キーとして id を使う。
    # ここで id を採番して保存しておかないと、後段の update_tacit_status(row_id=...)
    # で「IDが登録されていない」（=CSVに存在しない）になりやすい。
    # ------------------------------------------------------------

    # 既存CSVから次の id を採番する（欠損や文字列混入にも耐える）
    next_id = 0
    if csv_path.exists():
        try:
            df_old_for_id = pd.read_csv(csv_path)
            if "id" in df_old_for_id.columns and not df_old_for_id.empty:
                ids = pd.to_numeric(df_old_for_id["id"], errors="coerce").dropna()
                if not ids.empty:
                    next_id = int(ids.max()) + 1
            elif not df_old_for_id.empty:
                # id 列が無い場合は「行数」をベースに採番
                next_id = int(len(df_old_for_id))
        except Exception:
            # 読めない場合も最悪 0 から採番（上書きはしないので安全）
            next_id = 0

    record: Dict[str, Any] = {
        "id": next_id,
        "timestamp": dt.datetime.now().isoformat(),
        "case_id": case_id,
        "note": note,
        "category": category,
        "status": status,
        "author": author,
        "approver": approver,
    }
    if extra:
        record.update(extra)

    df_new = pd.DataFrame([record])

    if csv_path.exists():
        df_old = pd.read_csv(csv_path)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_csv(csv_path, index=False)


def merge_approved_notes_into_meta(
    index_dir: str | Path,
    *,
    tacit_csv: str | Path,
    target_col: str = "tacit_notes",
    approved_status: str = "approved",
) -> None:
    """
    承認済みの暗黙知を metadata.parquet にマージする。

    8_truble_ai.py の管理タブでやっていた処理のコア部分。
    """
    index_dir = Path(index_dir)
    tacit_csv = Path(tacit_csv)

    if not tacit_csv.exists():
        raise FileNotFoundError(f"Tacit knowledge CSV not found: {tacit_csv}")

    # リソースをロード（キャッシュされる）
    resources = load_resources(index_dir)
    meta = resources.meta.copy()
    cfg = resources.config

    tacit_df = pd.read_csv(tacit_csv)
    if tacit_df.empty:
        return

    # 承認済みのみ対象
    use_df = tacit_df[tacit_df["status"] == approved_status].copy()
    if use_df.empty:
        return

    # case_id ごとに note を結合するイメージ
    # 例: 同じ case_id に複数レコードあれば "\n---\n" などでまとめる
    grouped = (
        use_df.groupby("case_id")["note"]
        .apply(lambda s: "\n\n".join(str(x) for x in s if isinstance(x, str)))
        .reset_index()
    )

    # meta とマージ
    meta = meta.merge(
        grouped,
        how="left",
        left_on=cfg.id_col,
        right_on="case_id",
        suffixes=("", "_new"),
    )

    def _merge_notes(existing: Any, new: Any) -> Any:
        if pd.isna(new):
            return existing
        if pd.isna(existing) or existing is None:
            return new
        return f"{existing}\n\n---\n\n{new}"

    if target_col not in meta.columns:
        meta[target_col] = None

    meta[target_col] = [
        _merge_notes(old, new)
        for old, new in zip(meta[target_col], meta["note"])
    ]

    # 不要列の削除
    meta = meta.drop(columns=["case_id", "note"], errors="ignore")

    # 保存
    out_path = index_dir / "metadata.parquet"
    meta.to_parquet(out_path, index=False)

    # キャッシュを更新（次回 load_resources のため）
    # lru_cache は中身の更新まではしてくれないので、一度 cache_clear しておく
    load_resources.cache_clear()

import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional

# 既存: append_tacit_knowledge, merge_approved_notes_into_meta がある前提で追記


def load_tacit_knowledge(csv_path: Path) -> pd.DataFrame:
    """暗黙知CSVを読み込む。存在しなければ空DataFrameを返す。"""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        # append_tacit_knowledge が書き出す列に合わせておく
        cols = [
            "id",
            "case_id",
            "note",
            "category",
            "author",
            "approver",
            "status",
            "created_at",
            "extra",
        ]
        return pd.DataFrame(columns=cols)

    df = pd.read_csv(csv_path)

    # id カラムが無い場合はインデックスを id として付与
    if "id" not in df.columns:
        df = df.reset_index().rename(columns={"index": "id"})
    return df


def update_tacit_status(
    csv_path: Path,
    *,
    row_id: int,
    status: str = "approved",
    approver: Optional[str] = None,
) -> None:
    """指定idの暗黙知レコードのステータスを更新する。"""
    csv_path = Path(csv_path)
    df = load_tacit_knowledge(csv_path)

    # 安全側: int化して一致を見る
    df["id"] = df["id"].astype(int)

    if row_id not in df["id"].values:
        # 見つからなければ何もしない（必要なら例外でもよい）
        return

    mask = df["id"] == row_id
    df.loc[mask, "status"] = status
    if approver is not None:
        # カラムが無ければ追加
        if "approver" not in df.columns:
            df["approver"] = None
        df.loc[mask, "approver"] = approver

    df.to_csv(csv_path, index=False)

# =========================
# 分析用ヘルパ
# =========================

def load_feedback_stats(
    csv_path: str | Path,
) -> Dict[str, Any]:
    """
    search_feedback.csv 相当から簡単な統計値を返す。

    UI 側の「分析ページ」は、この関数の戻り値だけを見ればよい想定。
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return {
            "count": 0,
            "helpful_rate": None,
            "avg_solve_hours": None,
            "daily_helpful_rate": [],
        }

    df = pd.read_csv(csv_path)
    if df.empty:
        return {
            "count": 0,
            "helpful_rate": None,
            "avg_solve_hours": None,
            "daily_helpful_rate": [],
        }

    # helpful_rate
    helpful_rate = None
    if "helpful" in df.columns:
        helpful_rate = float(df["helpful"].mean())

    # 平均解決時間
    avg_solve = None
    if "solve_hours" in df.columns:
        # 数値に変換して NaN を除外
        solve = pd.to_numeric(df["solve_hours"], errors="coerce").dropna()
        if not solve.empty:
            avg_solve = float(solve.mean())

    # 日次 helpful 率（ロールアップ）
    daily: List[Dict[str, Any]] = []
    if "timestamp" in df.columns and "helpful" in df.columns:
        tmp = df.copy()
        tmp["date"] = pd.to_datetime(tmp["timestamp"], errors="coerce").dt.date
        tmp = tmp.dropna(subset=["date"])
        if not tmp.empty:
            grouped = tmp.groupby("date")["helpful"].mean().reset_index()
            for _, row in grouped.iterrows():
                daily.append(
                    {
                        "date": row["date"].isoformat(),
                        "helpful_rate": float(row["helpful"]),
                    }
                )

    return {
        "count": int(len(df)),
        "helpful_rate": helpful_rate,
        "avg_solve_hours": avg_solve,
        "daily_helpful_rate": daily,
    }
