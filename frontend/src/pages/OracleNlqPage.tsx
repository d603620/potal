// src/pages/OracleNlqPage.tsx
import React, { useEffect, useRef, useState } from "react";
import { queryOracleNlq } from "../api/oracleNlq";

type Preset = { id: string; title: string; question: string };
const LS_KEY = "oracle_nlq_presets_v2";

const DEFAULT_PRESETS: Preset[] = [
  { id: "p_day_runtime", title: "日別の稼働時間合計", question: "日別の稼働時間（UNTENJIKAN）の合計を出して" },
  { id: "p_recent_orders", title: "特定得意先の直近受注", question: "得意先コード 12345 の直近受注 10 件を出して" },
  { id: "p_monthly_sales", title: "月別売上（今年）", question: "今年の月別売上（合計）を表示して" },
];

function ResultTable({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const [pageSize, setPageSize] = useState<number>(50);
  const [page, setPage] = useState<number>(1);
  const [q, setQ] = useState<string>("");

  const safeColumns = columns ?? [];
  const filtered = q.trim()
    ? (rows ?? []).filter((r) =>
        safeColumns.some((c) => String(r?.[c] ?? "").toLowerCase().includes(q.trim().toLowerCase()))
      )
    : rows ?? [];

  const totalFiltered = filtered.length;
  const maxPage = Math.max(1, Math.ceil(totalFiltered / pageSize));
  const currentPage = Math.min(page, maxPage);
  const start = (currentPage - 1) * pageSize;
  const slice = filtered.slice(start, start + pageSize);

  const isProbablyNumber = (v: any) => {
    if (v == null) return false;
    if (typeof v === "number") return true;
    const s = String(v).trim();
    if (s === "") return false;
    return !Number.isNaN(Number(s));
  };

  // 文字数に応じて列の最小幅を決める（最低限・安定重視）
  const charToPx = (len: number) => Math.min(420, Math.max(80, len * 14));

  const columnWidths = React.useMemo(() => {
    const map: Record<string, number> = {};
    safeColumns.forEach((c) => {
      const headerLen = c.length;
      // heavyになりすぎないよう最大 200 行分だけ見て推定
      const sample = (rows ?? []).slice(0, 200);
      let bodyMaxLen = 0;
      for (const r of sample) {
        const l = String(r?.[c] ?? "").length;
        if (l > bodyMaxLen) bodyMaxLen = l;
      }
      const maxLen = Math.max(headerLen, bodyMaxLen);
      map[c] = charToPx(maxLen);
    });
    return map;
  }, [safeColumns, rows]);

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <div className="dnp-note">件数：{totalFiltered.toLocaleString()}</div>

        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input
            className="dnp-text-input"
            style={{ width: 260 }}
            placeholder="結果内検索（部分一致）"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />

          <label className="dnp-note" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
            表示件数
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              style={{ border: "1px solid rgba(0,0,0,0.15)", borderRadius: 8, padding: "6px 10px" }}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          </label>

          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button className="dnp-btn" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={currentPage <= 1}>
              前へ
            </button>
            <div className="dnp-note">
              {currentPage} / {maxPage}
            </div>
            <button
              className="dnp-btn"
              onClick={() => setPage((p) => Math.min(maxPage, p + 1))}
              disabled={currentPage >= maxPage}
            >
              次へ
            </button>
          </div>
        </div>
      </div>

      <div
        style={{
          marginTop: 10,
          overflow: "auto",
          border: "1px solid rgba(0,0,0,0.08)",
          borderRadius: 12,
          maxHeight: 520,
          background: "#fff",
        }}
      >
        <table
          style={{
            width: "max-content", // 列幅を生かして横に伸ばす（親divでスクロール）
            minWidth: "100%",
            borderCollapse: "separate",
            borderSpacing: 0,
            tableLayout: "fixed",
            fontSize: 13,
          }}
        >
          <thead>
            <tr>
              {safeColumns.map((c) => (
                <th
                  key={c}
                  title={c}
                  style={{
                    position: "sticky",
                    top: 0,
                    zIndex: 1,
                    textAlign: "left",
                    padding: "10px 10px",
                    background: "#f7f8fa",
                    borderBottom: "1px solid rgba(0,0,0,0.10)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    minWidth: columnWidths[c],
                  }}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {slice.map((r, idx) => (
              <tr key={start + idx} style={{ background: (start + idx) % 2 === 0 ? "#fff" : "#fbfbfc" }}>
                {safeColumns.map((c) => {
                  const v = r?.[c];
                  const right = isProbablyNumber(v);
                  return (
                    <td
                      key={c}
                      title={v == null ? "" : String(v)}
                      style={{
                        padding: "9px 10px",
                        borderBottom: "1px solid rgba(0,0,0,0.06)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        textAlign: right ? "right" : "left",
                        minWidth: columnWidths[c],
                      }}
                      onDoubleClick={() => {
                        const text = v == null ? "" : String(v);
                        navigator.clipboard?.writeText(text);
                      }}
                    >
                      {v == null ? "" : String(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="dnp-note" style={{ marginTop: 8 }}>
        ヒント：セルをダブルクリックすると値をコピーできます。
      </div>
    </div>
  );
}

export default function OracleNlqPage() {
  // query state
  const [question, setQuestion] = useState("");
  const [sql, setSql] = useState("");
  const [rows, setRows] = useState<Record<string, any>[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // presets
  const [presets, setPresets] = useState<Preset[]>([]);
  const [autoRunPreset, setAutoRunPreset] = useState(false);

  // modal & edit
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editPreset, setEditPreset] = useState<Preset | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const importTextRef = useRef<HTMLTextAreaElement | null>(null);

  // drag
  const dragIndexRef = useRef<number | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) setPresets(JSON.parse(raw));
      else {
        setPresets(DEFAULT_PRESETS);
        localStorage.setItem(LS_KEY, JSON.stringify(DEFAULT_PRESETS));
      }
    } catch {
      setPresets(DEFAULT_PRESETS);
    }
  }, []);

  function savePresets(next: Preset[]) {
    setPresets(next);
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }

  async function runQuery(q: string) {
    setError(null);
    setSql("");
    setRows([]);
    setColumns([]);
    setLoading(true);
    try {
      const r = await queryOracleNlq({ question: q, limit: 200 });
      setSql(r.sql ?? "");
      setColumns(r.columns ?? []);
      setRows(r.rows ?? []);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  function handlePresetClick(p: Preset) {
    setQuestion(p.question);
    if (autoRunPreset) void runQuery(p.question);
  }

  function handleAddPreset() {
    setEditPreset({ id: `p_${Date.now()}`, title: "", question: "" });
    setIsEditModalOpen(true);
  }

  function handleEditPreset(p: Preset) {
    setEditPreset(p);
    setIsEditModalOpen(true);
  }

  function handleSaveEditPreset(p: Preset) {
    const exists = presets.some((x) => x.id === p.id);
    const next = exists ? presets.map((x) => (x.id === p.id ? p : x)) : [p, ...presets];
    savePresets(next);
    setIsEditModalOpen(false);
    setEditPreset(null);
  }

  function handleDeletePreset(id: string) {
    if (!confirm("テンプレートを削除してよいですか？")) return;
    savePresets(presets.filter((p) => p.id !== id));
  }

  // drag handlers
  function onDragStart(e: React.DragEvent, index: number) {
    dragIndexRef.current = index;
    e.dataTransfer.effectAllowed = "move";
  }
  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }
  function onDrop(e: React.DragEvent, index: number) {
    e.preventDefault();
    const from = dragIndexRef.current;
    if (from == null || from === index) return;
    const next = [...presets];
    const [item] = next.splice(from, 1);
    next.splice(index, 0, item);
    savePresets(next);
    dragIndexRef.current = null;
  }

  // preset export/import
  function exportPresets() {
    const blob = new Blob([JSON.stringify(presets, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `oracle_nlq_presets_${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function importPresetsFromText(text: string) {
    try {
      const parsed = JSON.parse(text) as Preset[];
      if (!Array.isArray(parsed)) throw new Error("JSON must be an array");
      for (const p of parsed) if (!p.id || !p.title || !p.question) throw new Error("Each item needs id/title/question");
      savePresets(parsed);
      setIsImportModalOpen(false);
      alert("インポートしました。");
    } catch (e: any) {
      alert("インポート失敗: " + (e?.message ?? String(e)));
    }
  }

  function importPresetsMerge(text: string) {
    try {
      const parsed = JSON.parse(text) as Preset[];
      if (!Array.isArray(parsed)) throw new Error("JSON must be an array");
      const next = [...parsed, ...presets];
      savePresets(next);
      setIsImportModalOpen(false);
      alert("マージしました。");
    } catch (e: any) {
      alert("インポート失敗: " + (e?.message ?? String(e)));
    }
  }

  function handleImportFile(file: File, merge = false) {
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      try {
        const parsed = JSON.parse(text) as Preset[];
        if (!Array.isArray(parsed)) throw new Error("JSON must be an array");
        const next = merge ? [...parsed, ...presets] : parsed;
        savePresets(next);
        alert("ファイルから読み込みました。");
      } catch (e: any) {
        alert("ファイル読み込み失敗: " + (e?.message ?? String(e)));
      }
    };
    reader.readAsText(file);
  }

  // CSV export for current results
  function exportCsv() {
    if (!columns || columns.length === 0 || rows.length === 0) {
      alert("出力するデータがありません。");
      return;
    }

    function escapeCsvField(value: any) {
      if (value == null) return "";
      const s = String(value);
      if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
      return s;
    }

    const csv = [
      columns.map((c) => escapeCsvField(c)).join(","),
      ...rows.map((r) => columns.map((c) => escapeCsvField(r?.[c] ?? "")).join(",")),
    ].join("\n");

    const bom = "\uFEFF"; // Excel対策
    const blob = new Blob([bom + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    a.download = `oracle_nlq_result_${ts}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="portal-main">
      <div className="dnp-page">
        <div className="dnp-card oracle-nlq-hero">
          <div className="dnp-page-eyebrow">ORACLE NLQ</div>
          <h1 className="dnp-section-title">データ問い合わせ</h1>
          <div className="dnp-page-subtitle">自然文で Oracle DB に問い合わせできます。ただし最大200件データまでです。</div>
        </div>

        {/* input card */}
        <div className="dnp-card" style={{ gap: 12 }}>
          <div className="dnp-field-label">質問内容</div>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <input
              className="dnp-text-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="例：日別の稼働時間（UNTENJIKAN）の合計を出して"
              style={{ flex: 1 }}
            />
            <button className="dnp-btn dnp-btn-primary" onClick={() => void runQuery(question)} disabled={loading || !question.trim()}>
              {loading ? "実行中…" : "実行"}
            </button>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
            <div style={{ fontSize: 13, color: "var(--text-sub)" }}>質問テンプレート</div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {presets.map((p) => (
                <button key={p.id} className="dnp-btn" title={p.question} onClick={() => handlePresetClick(p)}>
                  {p.title}
                </button>
              ))}
            </div>

            <label style={{ marginLeft: 8, display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input type="checkbox" checked={autoRunPreset} onChange={(e) => setAutoRunPreset(e.target.checked)} />
              <span style={{ fontSize: 13 }}>クリックで自動実行</span>
            </label>

            <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
              <button className="dnp-btn" onClick={handleAddPreset}>プリセット追加</button>
              <button className="dnp-btn" onClick={() => setIsImportModalOpen(true)}>インポート / エクスポート</button>
              <button className="dnp-btn" onClick={exportPresets}>エクスポート</button>
              <label className="dnp-btn" style={{ cursor: "pointer" }}>
                ファイルからインポート
                <input
                  type="file"
                  accept="application/json"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleImportFile(f, false);
                    e.currentTarget.value = "";
                  }}
                  style={{ display: "none" }}
                />
              </label>
            </div>
          </div>
        </div>

        {/* preset manager */}
        <div className="dnp-card" style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div className="dnp-h3">テンプレート管理</div>
              <div className="dnp-note">ドラッグして順序を入れ替えられます</div>
            </div>
          </div>

          <ul style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            {presets.map((p, i) => (
              <li
                key={p.id}
                draggable
                onDragStart={(e) => onDragStart(e, i)}
                onDragOver={onDragOver}
                onDrop={(e) => onDrop(e, i)}
                className="dnp-card"
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12 }}
              >
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <div style={{ color: "var(--text-sub)", fontSize: 12 }}>#{i + 1}</div>
                  <div>
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                    <div style={{ fontSize: 13, color: "var(--text-sub)" }}>{p.question}</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  <button className="dnp-btn" onClick={() => handlePresetClick(p)}>入力</button>
                  <button className="dnp-btn" onClick={() => handleEditPreset(p)}>編集</button>
                  <button className="dnp-btn dnp-btn-danger" onClick={() => handleDeletePreset(p.id)}>削除</button>
                </div>
              </li>
            ))}
            {presets.length === 0 && <div className="dnp-note">テンプレートがありません。追加してください。</div>}
          </ul>
        </div>

        {/* results card */}
        <div className="dnp-card" style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="dnp-h3">実行結果</div>
          </div>

          {error && <div className="edu-error" style={{ marginTop: 8 }}>{error}</div>}

          {sql && (
            <div style={{ marginTop: 8 }}>
              <div className="dnp-note">生成 SQL</div>
              <pre className="dnp-pre" style={{ marginTop: 6 }}>{sql}</pre>
            </div>
          )}

          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <button className="dnp-dnp-btn dnp-btn-primary" onClick={exportCsv} disabled={rows.length === 0}>CSV出力</button>
          </div>

          {rows.length > 0 ? <ResultTable columns={columns} rows={rows} /> : <div className="dnp-note" style={{ marginTop: 8 }}>結果が空です（まだ実行していないか、結果がありません）。</div>}
        </div>

        {/* Edit modal */}
        {isEditModalOpen && editPreset && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.35)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1000,
              padding: 16,
            }}
            role="dialog"
            aria-modal="true"
          >
            <div
              style={{
                background: "#fff",
                borderRadius: 12,
                width: "min(720px, 100%)",
                boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: 16,
                  borderBottom: "1px solid rgba(0,0,0,0.08)",
                }}
              >
                <div style={{ fontWeight: 700 }}>プリセット編集</div>
                <button
                  className="dnp-btn"
                  onClick={() => {
                    setIsEditModalOpen(false);
                    setEditPreset(null);
                  }}
                  aria-label="close"
                >
                  ✕
                </button>
              </div>

              <div style={{ padding: 16, display: "grid", gap: 10 }}>
                <label className="dnp-field-label">テンプレート名</label>
                <input
                  className="dnp-text-input"
                  style={{ width: "100%" }}
                  value={editPreset.title}
                  onChange={(e) => setEditPreset({ ...editPreset, title: e.target.value })}
                />

                <label className="dnp-field-label" style={{ marginTop: 4 }}>質問文（自然文）</label>
                <textarea
                  className="dnp-textarea"
                  style={{ width: "100%", minHeight: 120 }}
                  value={editPreset.question}
                  onChange={(e) => setEditPreset({ ...editPreset, question: e.target.value })}
                />
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: 8,
                  padding: 16,
                  borderTop: "1px solid rgba(0,0,0,0.08)",
                }}
              >
                <button
                  className="dnp-btn"
                  onClick={() => {
                    setIsEditModalOpen(false);
                    setEditPreset(null);
                  }}
                >
                  キャンセル
                </button>
                <button
                  className="dnp-btn dnp-btn-primary"
                  onClick={() => {
                    if (!editPreset.title.trim()) return alert("テンプレート名を入力してください");
                    if (!editPreset.question.trim()) return alert("質問文を入力してください");
                    handleSaveEditPreset(editPreset);
                  }}
                >
                  保存
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Import modal */}
        {isImportModalOpen && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.35)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1000,
              padding: 16,
            }}
            role="dialog"
            aria-modal="true"
          >
            <div
              style={{
                background: "#fff",
                borderRadius: 12,
                width: "min(900px, 100%)",
                boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: 16,
                  borderBottom: "1px solid rgba(0,0,0,0.08)",
                }}
              >
                <div style={{ fontWeight: 700 }}>インポート / エクスポート</div>
                <button className="dnp-btn" onClick={() => setIsImportModalOpen(false)} aria-label="close">✕</button>
              </div>

              <div style={{ padding: 16, display: "grid", gap: 10 }}>
                <div className="dnp-note">JSON 配列形式のプリセット（id,title,question）を入力してください。</div>
                <textarea ref={importTextRef} className="dnp-textarea" style={{ width: "100%", minHeight: 220 }} />
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: 8,
                  padding: 16,
                  borderTop: "1px solid rgba(0,0,0,0.08)",
                  flexWrap: "wrap",
                }}
              >
                <button className="dnp-btn" onClick={() => setIsImportModalOpen(false)}>閉じる</button>
                <button
                  className="dnp-btn"
                  onClick={() => {
                    const text = importTextRef.current?.value ?? "";
                    if (!text.trim()) return alert("テキストを入力してください");
                    importPresetsFromText(text);
                  }}
                >
                  上書きインポート
                </button>
                <button
                  className="dnp-btn"
                  onClick={() => {
                    const text = importTextRef.current?.value ?? "";
                    if (!text.trim()) return alert("テキストを入力してください");
                    importPresetsMerge(text);
                  }}
                >
                  マージインポート
                </button>
                <button className="dnp-btn dnp-btn-primary" onClick={() => exportPresets()}>
                  現在のエクスポート
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
