import React, { useState } from "react";
import axios from "axios";

type TroubleRecord = {
  internal_index: number;
  id?: string;
  [key: string]: any;
};

type SearchResponse = {
  count: number;
  results: TroubleRecord[];
};

const TroubleSearch: React.FC = () => {
  const [query, setQuery] = useState("");
  const [years, setYears] = useState<number | undefined>(undefined);
  const [severityMin, setSeverityMin] = useState<number | undefined>(1);
  const [severityMax, setSeverityMax] = useState<number | undefined>(5);
  const [productsText, setProductsText] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [topK, setTopK] = useState(20);
  const [alpha, setAlpha] = useState(0.5);

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<TroubleRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [tacitModalOpen, setTacitModalOpen] = useState(false);
  const [tacitTarget, setTacitTarget] = useState<TroubleRecord | null>(null);
  const [tacitNote, setTacitNote] = useState("");
  const [tacitCategory, setTacitCategory] = useState("");
  const [tacitAuthor, setTacitAuthor] = useState("");

  const parseCsvList = (text: string): string[] | undefined => {
    const arr = text
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    return arr.length > 0 ? arr : undefined;
  };

  const handleSearch = async () => {
    setError(null);
    if (!query.trim()) {
      setError("検索キーワードを入力してください。");
      return;
    }

    setLoading(true);
    try {
      const params: any = {
        q: query,
        top_k: topK,
        alpha,
      };
      if (years !== undefined && years !== null) params.years = years;
      if (severityMin !== undefined && severityMin !== null)
        params.severity_min = severityMin;
      if (severityMax !== undefined && severityMax !== null)
        params.severity_max = severityMax;

      const products = parseCsvList(productsText);
      const tags = parseCsvList(tagsText);
      if (products) params.products = products;
      if (tags) params.tags = tags;

      const res = await axios.get<SearchResponse>("/api/trouble/search", {
        params,
      });
      setResults(res.data.results ?? []);
    } catch (e: any) {
      console.error(e);
      setError("検索中にエラーが発生しました。");
    } finally {
      setLoading(false);
    }
  };

  const sendFeedback = async (
    rec: TroubleRecord,
    helpful: boolean,
    solveHours?: number
  ) => {
    try {
      await axios.post("/api/trouble/feedback", {
        query,
        case_id: rec.id ?? rec.internal_index,
        helpful,
        solve_hours: solveHours ?? null,
        extra: {},
      });
      // 軽いフィードバックなのでトーストなど付けてもよい
      alert("フィードバックを送信しました。");
    } catch (e) {
      console.error(e);
      alert("フィードバック送信に失敗しました。");
    }
  };

  const openTacitModal = (rec: TroubleRecord) => {
    setTacitTarget(rec);
    setTacitNote("");
    setTacitCategory("");
    setTacitAuthor("");
    setTacitModalOpen(true);
  };

  const submitTacit = async () => {
    if (!tacitTarget) return;
    if (!tacitNote.trim()) {
      alert("暗黙知メモを入力してください。");
      return;
    }
    try {
      await axios.post("/api/trouble/tacit", {
        case_id: tacitTarget.id ?? tacitTarget.internal_index,
        note: tacitNote,
        category: tacitCategory || null,
        author: tacitAuthor || null,
        approver: null,
        status: "pending",
        extra: {},
      });
      alert("暗黙知を登録しました（承認待ち）。");
      setTacitModalOpen(false);
    } catch (e) {
      console.error(e);
      alert("暗黙知の登録に失敗しました。");
    }
  };

  const renderField = (rec: TroubleRecord, key: string, label: string) => {
    const val = rec[key];
    if (val === undefined || val === null || val === "") return null;
    return (
      <div className="text-sm mb-1">
        <span className="font-semibold mr-1">{label}:</span>
        <span>{String(val)}</span>
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl md:text-3xl font-bold mt-1 text-white">トラブル事例検索</h1>

      {/* 検索条件エリア */}
      <div className="bg-white shadow rounded-xl p-4 mb-6 border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-1">
              キーワード
            </label>
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="例）印刷不良　ドット抜け　など"
            />
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-xs font-semibold mb-1">
                直近〇年
              </label>
              <input
                type="number"
                className="w-full border rounded px-2 py-1 text-sm"
                value={years ?? ""}
                onChange={(e) =>
                  setYears(
                    e.target.value === ""
                      ? undefined
                      : Number(e.target.value)
                  )
                }
                min={0}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1">
                重大度Min
              </label>
              <input
                type="number"
                className="w-full border rounded px-2 py-1 text-sm"
                value={severityMin ?? ""}
                onChange={(e) =>
                  setSeverityMin(
                    e.target.value === ""
                      ? undefined
                      : Number(e.target.value)
                  )
                }
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1">
                重大度Max
              </label>
              <input
                type="number"
                className="w-full border rounded px-2 py-1 text-sm"
                value={severityMax ?? ""}
                onChange={(e) =>
                  setSeverityMax(
                    e.target.value === ""
                      ? undefined
                      : Number(e.target.value)
                  )
                }
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">
              製品（カンマ区切り）
            </label>
            <input
              className="w-full border rounded px-2 py-1 text-sm"
              value={productsText}
              onChange={(e) => setProductsText(e.target.value)}
              placeholder="PRODUCT-A, PRODUCT-B"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">
              タグ（カンマ区切り）
            </label>
            <input
              className="w-full border rounded px-2 py-1 text-sm"
              value={tagsText}
              onChange={(e) => setTagsText(e.target.value)}
              placeholder="剥離, ラミネート …"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold mb-1">
                top_k
              </label>
              <input
                type="number"
                className="w-full border rounded px-2 py-1 text-sm"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value || 0))}
                min={1}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1">
                alpha（0〜1）
              </label>
              <input
                type="number"
                step="0.1"
                min={0}
                max={1}
                className="w-full border rounded px-2 py-1 text-sm"
                value={alpha}
                onChange={(e) => setAlpha(Number(e.target.value || 0))}
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-semibold disabled:opacity-60"
          >
            {loading ? "検索中..." : "検索する"}
          </button>
          {error && <div className="text-sm text-red-600">{error}</div>}
        </div>
      </div>

      {/* 検索結果 */}
      <div>
        <div className="flex items-center justify-between mb-2 text-white">
          <h2 className="text-lg font-semibold">検索結果</h2>
          <span className="text-sm text-gray-500">
            {results.length} 件ヒット
          </span>
        </div>

        {results.length === 0 && (
          <div className="text-sm text-gray-500 text-white">
            検索結果がありません。条件を変えて再度お試しください。
          </div>
        )}

        <div className="space-y-4">
          {results.map((rec) => (
            <div
              key={rec.internal_index}
              className="bg-white border border-gray-200 rounded-xl shadow-sm p-4"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="text-sm text-gray-500">
                    ID: {rec.id ?? rec.internal_index}
                  </div>
                  <div className="text-base font-semibold">
                    {rec.title || rec.summary || "(タイトル未設定)"}
                  </div>
                </div>
              </div>

              <div className="mt-2 space-y-1">
                {renderField(rec, "date", "発生日")}
                {renderField(rec, "severity", "重大度")}
                {renderField(rec, "product", "製品")}
                {renderField(rec, "tags", "タグ")}
              </div>

              {rec.summary && (
                <div className="mt-2">
                  <div className="text-xs font-semibold mb-1">概要</div>
                  <p className="text-sm whitespace-pre-wrap">
                    {String(rec.summary)}
                  </p>
                </div>
              )}

              {rec.root_cause && (
                <div className="mt-2">
                  <div className="text-xs font-semibold mb-1">真因</div>
                  <p className="text-sm whitespace-pre-wrap">
                    {String(rec.root_cause)}
                  </p>
                </div>
              )}

              {rec.countermeasure && (
                <div className="mt-2">
                  <div className="text-xs font-semibold mb-1">対策</div>
                  <p className="text-sm whitespace-pre-wrap">
                    {String(rec.countermeasure)}
                  </p>
                </div>
              )}

              {rec.tacit_notes && (
                <div className="mt-2 border-t pt-2">
                  <div className="text-xs font-semibold mb-1">暗黙知</div>
                  <p className="text-sm whitespace-pre-wrap">
                    {String(rec.tacit_notes)}
                  </p>
                </div>
              )}

              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="px-3 py-1 rounded-full bg-green-600 text-white text-xs"
                  onClick={() => {
                    const input = window.prompt(
                      "解決までの時間（時間）を入力してください（任意）",
                      "0"
                    );
                    const hours = input ? Number(input) : undefined;
                    sendFeedback(rec, true, isNaN(hours || NaN) ? undefined : hours);
                  }}
                >
                  有用だった
                </button>
                <button
                  className="px-3 py-1 rounded-full bg-gray-500 text-white text-xs"
                  onClick={() => sendFeedback(rec, false)}
                >
                  有用でなかった
                </button>
                <button
                  className="px-3 py-1 rounded-full bg-orange-500 text-white text-xs"
                  onClick={() => openTacitModal(rec)}
                >
                  暗黙知を追記
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 暗黙知モーダル */}
      {tacitModalOpen && tacitTarget && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg w-full max-w-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold text-lg">暗黙知の登録</h3>
              <button
                className="text-sm text-gray-500"
                onClick={() => setTacitModalOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="text-xs text-gray-500 mb-2">
              対象ID: {tacitTarget.id ?? tacitTarget.internal_index}
            </div>

            <div className="mb-3">
              <label className="block text-xs font-semibold mb-1">
                カテゴリ（任意）
              </label>
              <input
                className="w-full border rounded px-2 py-1 text-sm"
                value={tacitCategory}
                onChange={(e) => setTacitCategory(e.target.value)}
              />
            </div>

            <div className="mb-3">
              <label className="block text-xs font-semibold mb-1">
                登録者（任意）
              </label>
              <input
                className="w-full border rounded px-2 py-1 text-sm"
                value={tacitAuthor}
                onChange={(e) => setTacitAuthor(e.target.value)}
              />
            </div>

            <div className="mb-3">
              <label className="block text-xs font-semibold mb-1">
                暗黙知メモ
              </label>
              <textarea
                className="w-full border rounded px-2 py-1 text-sm h-32"
                value={tacitNote}
                onChange={(e) => setTacitNote(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                className="px-3 py-1 rounded text-xs border"
                onClick={() => setTacitModalOpen(false)}
              >
                キャンセル
              </button>
              <button
                className="px-3 py-1 rounded text-xs bg-blue-600 text-white"
                onClick={submitTacit}
              >
                登録する
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TroubleSearch;
