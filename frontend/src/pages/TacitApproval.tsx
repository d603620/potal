import React, { useEffect, useState } from "react";
import axios from "axios";

type TacitRecord = {
  id: number;
  case_id: string | number;
  note: string;
  category?: string | null;
  author?: string | null;
  approver?: string | null;
  status: string;
  created_at?: string | null;
  [key: string]: any;
};

type TacitListResponse = {
  count: number;
  results: TacitRecord[];
};

const TacitApproval: React.FC = () => {
  const [records, setRecords] = useState<TacitRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPending = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<TacitListResponse>(
        "/api/trouble/tacit/list",
        {
          params: { status: "pending" },
        }
      );
      setRecords(res.data.results ?? []);
    } catch (e) {
      console.error(e);
      setError("暗黙知の取得に失敗しました。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const approveOne = async (rec: TacitRecord) => {
    const approver = window.prompt(
      "承認者名を入力してください（任意）",
      rec.approver || ""
    );
    try {
      await axios.post("/api/trouble/tacit/approve", {
        row_id: rec.id,
        approver: approver && approver.trim().length > 0 ? approver : null,
      });
      // 承認済みリストから除外するため再取得
      await fetchPending();
    } catch (e) {
      console.error(e);
      alert("承認に失敗しました。");
    }
  };

  const applyApproved = async () => {
    if (!window.confirm("承認済みの暗黙知を metadata に反映しますか？")) {
      return;
    }
    setApplying(true);
    try {
      await axios.post("/api/trouble/tacit/apply");
      alert("承認済み暗黙知を反映しました。");
    } catch (e) {
      console.error(e);
      alert("反映に失敗しました。");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">暗黙知 承認画面</h1>
        <div className="flex gap-2">
          <button
            className="px-3 py-2 rounded text-sm border"
            onClick={fetchPending}
            disabled={loading}
          >
            再読み込み
          </button>
          <button
            className="px-3 py-2 rounded text-sm bg-blue-600 text-white disabled:opacity-60"
            onClick={applyApproved}
            disabled={applying}
          >
            {applying ? "反映中..." : "承認済みを反映"}
          </button>
        </div>
      </div>

      {error && <div className="mb-3 text-sm text-red-600">{error}</div>}

      <div className="mb-3 text-sm text-gray-600">
        承認待ち件数: {records.length} 件
      </div>

      {records.length === 0 && (
        <div className="text-sm text-gray-500">
          承認待ちの暗黙知はありません。
        </div>
      )}

      <div className="space-y-3">
        {records.map((rec) => (
          <div
            key={rec.id}
            className="bg-white border border-gray-200 rounded-xl shadow-sm p-4"
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <div className="text-xs text-gray-500">
                  ID: {rec.id} / Case: {rec.case_id}
                </div>
                {rec.category && (
                  <div className="text-xs text-gray-500">
                    カテゴリ: {rec.category}
                  </div>
                )}
                <div className="text-xs text-gray-500">
                  登録者: {rec.author || "-"}
                  {rec.created_at && ` / 登録日: ${rec.created_at}`}
                </div>
                {rec.approver && (
                  <div className="text-xs text-gray-500">
                    承認者(既存): {rec.approver}
                  </div>
                )}
              </div>
              <button
                className="px-3 py-1 rounded-full text-xs bg-green-600 text-white"
                onClick={() => approveOne(rec)}
              >
                承認する
              </button>
            </div>

            <div className="text-xs font-semibold mb-1">暗黙知メモ</div>
            <p className="text-sm whitespace-pre-wrap">{rec.note}</p>

            {rec.extra && (
              <div className="mt-2 text-xs text-gray-500">
                付加情報: {JSON.stringify(rec.extra)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TacitApproval;
