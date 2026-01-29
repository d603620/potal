import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * Filejson.tsx
 * - FastAPI 連携用の JSON ツール画面
 * - 編集用テキスト state と JSON オブジェクト state を分離
 * - 既存のエンドポイント:
 *   - GET    /health
 *   - POST   /files/preview                 (FormData: file)
 *   - POST   /api/parse                     (FormData: file)
 *   - POST   /api/hitei-dedupe              (FormData: file)
 *   - POST   /api/generate                  (JSON: { po_text, hitei_text, instruction? })
 *   - POST   /api/diff                      (JSON: { current_json, preview_json })
 *   - GET    /api/tree                      (任意)
 */

// API ベースURL（Vite の .env で VITE_API_BASE を指定可能）
const apiBase =
  (import.meta as any)?.env?.VITE_API_BASE || window.location.origin;

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postBlob(path: string, body: unknown): Promise<Blob> {
  const res = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${t}`);
  }
  return res.blob();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`);
  }
  return res.json();
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${apiBase}${path}`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`);
  }
  return res.json();
}

export default function FileJsonPage() {
  // 健康チェック / tree など（任意）
  const [health, setHealth] = useState<string>("");
//  const [tree, setTree] = useState<string>("");

  // プレビュー（CSV/Excel）
  const [previewName, setPreviewName] = useState<string>("");
  const [previewCSV, setPreviewCSV] = useState<string>("");
  const [previewTruncated, setPreviewTruncated] = useState<boolean>(false);

  // テキスト（PO / 該非）
  const [targetField, setTargetField] = useState<"po" | "hitei">("po");
  const [poText, setPoText] = useState<string>("");
  const [hiteiText, setHiteiText] = useState<string>("");
  const [instruction, setInstruction] = useState<string>("");

  // 生成・差分
  const [generateBusy, setGenerateBusy] = useState(false);
  const [draft, setDraft] = useState<any>(null);

  // ← 重要: 編集用テキストと JSON オブジェクトを分離
  const [currentJson, setCurrentJson] = useState<any>({});
  const [currentText, setCurrentText] = useState<string>("{}"); // エディタ表示用

  const [diffText, setDiffText] = useState<string>("");

  // input refs
  const fileInput = useRef<HTMLInputElement | null>(null);
  const hiteiInput = useRef<HTMLInputElement | null>(null);

  const prettyDraft = useMemo(
    () => (draft ? JSON.stringify(draft, null, 2) : ""),
    [draft]
  );

  // 初期同期（必要なら）
  useEffect(() => {
    setCurrentText(JSON.stringify(currentJson || {}, null, 2));
  }, []); // 初回のみ

  // ユーティリティ
  const onPickFile = () => fileInput.current?.click();
  const onPickHitei = () => hiteiInput.current?.click();

  const checkHealth = async () => {
    try {
      const h = await getJSON<{ status?: string; ok?: boolean }>("/health");
      setHealth(h.status || (h.ok ? "ok" : ""));
    } catch {
      setHealth("NG");
    }
  };

  // const loadTree = async () => {
  //   try {
  //     const t = await getJSON<{ text: string }>("/api/tree");
  //     setTree(t.text || "");
  //   } catch {
  //     setTree("");
  //   }
  // };

  // --- アップロード処理 ---
  const handlePreviewUpload = async (f: File) => {
    const fd = new FormData();
    fd.append("file", f);
    const data = await postForm<{
      name: string;
      ext: string;
      preview_csv: string;
      truncated: boolean;
    }>("/files/preview", fd);
    setPreviewName(data.name);
    setPreviewCSV(data.preview_csv);
    setPreviewTruncated(data.truncated);
  };

  const handleParseUpload = async (f: File) => {
    const fd = new FormData();
    fd.append("file", f);
    const data = await postForm<{ ok: boolean; text: string }>("/api/parse", fd);
    if (targetField === "po") setPoText(data.text);
    else setHiteiText(data.text);
  };

  const handleHiteiDedupe = async (f: File) => {
    const fd = new FormData();
    fd.append("file", f);
    const data = await postForm<{ ok: boolean; text: string; message: string }>(
      "/api/hitei-dedupe",
      fd
    );
    setHiteiText(data.text);
    alert(data.message);
  };

  const onFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      const lower = f.name.toLowerCase();
      if (lower.endsWith(".csv") || lower.endsWith(".xlsx") || lower.endsWith(".xls")) {
        await handlePreviewUpload(f);
      }
      await handleParseUpload(f);
    } catch (err: any) {
      alert(`Upload failed: ${err.message || err}`);
    } finally {
      e.currentTarget.value = "";
    }
  };

  const onHiteiSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      await handleHiteiDedupe(f);
    } catch (err: any) {
      alert(`Upload failed: ${err.message || err}`);
    } finally {
      e.currentTarget.value = "";
    }
  };

  // --- 生成＆差分 ---
  const doGenerate = async () => {
    setGenerateBusy(true);
    try {
      const payload = {
        po_text: poText,
        hitei_text: hiteiText,
        instruction: instruction || null,
      };
      const data = await postJSON<{ ok: boolean; data: any }>(
        "/api/generate",
        payload
      );
      setDraft(data.data);
    } catch (err: any) {
      alert(`Generate failed: ${err.message || err}`);
    } finally {
      setGenerateBusy(false);
    }
  };

  const doDiff = async () => {
    try {
      const data = await postJSON<{ ok: boolean; diff: string }>("/api/diff", {
        current_json: currentJson || {},
        preview_json: draft || {},
      });
      setDiffText(data.diff);
    } catch (err: any) {
      alert(`Diff failed: ${err.message || err}`);
    }
  };

  // ✅ ← ここに downloadExcel を追加
  const downloadExcel = async (useDraft = true) => {
    try {
      const data = useDraft && draft ? draft : currentJson || {};
      const blob = await postBlob("/api/excel/render", { data });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "generated.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Excel export failed: ${err.message || err}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-7xl p-4 flex items-center gap-4">
          <h1 className="text-2xl font-bold">JSONツール（PO/該非）</h1>
          <button
            onClick={checkHealth}
            className="ml-auto rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-100"
          >
            Health
          </button>
          <span
            className={`text-sm ${
              health === "ok" ? "text-green-600" : "text-gray-400"
            }`}
          >
            {health || ""}
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT: Upload & Text Inputs */}
        <section className="space-y-4">
          <div className="rounded-2xl border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="text-sm font-medium">抽出ターゲット:</div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  className="accent-blue-600"
                  checked={targetField === "po"}
                  onChange={() => setTargetField("po")}
                />
                発注書 (PO)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  className="accent-blue-600"
                  checked={targetField === "hitei"}
                  onChange={() => setTargetField("hitei")}
                />
                該非判定書
              </label>
              <div className="ml-auto flex gap-2">
                <button
                  onClick={onPickFile}
                  className="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-100"
                >
                  ファイル選択
                </button>
                <input
                  ref={fileInput}
                  type="file"
                  className="hidden"
                  onChange={onFileSelected}
                />
              </div>
            </div>

            {previewName && (
              <div className="mt-4">
                <div className="mb-1 text-sm text-gray-500">
                  プレビュー: {previewName}
                  {previewTruncated ? "（一部省略）" : ""}
                </div>
                <pre className="h-40 overflow-auto rounded-lg bg-gray-50 p-3 text-xs border">
                  {previewCSV}
                </pre>
              </div>
            )}
          </div>

          <div className="rounded-2xl border bg-white p-4 shadow-sm">
            <div className="mb-2 text-sm font-semibold">
              該非ファイルの重複チェック & 抽出
            </div>
            <div className="flex gap-2">
              <button
                onClick={onPickHitei}
                className="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-100"
              >
                該非ファイル選択
              </button>
              <input
                ref={hiteiInput}
                type="file"
                className="hidden"
                onChange={onHiteiSelected}
              />
            </div>
          </div>

          <div className="rounded-2xl border bg-white p-4 shadow-sm space-y-3">
            <div>
              <div className="mb-1 text-sm font-medium">発注書テキスト (PO)</div>
              <textarea
                className="w-full h-40 rounded-lg border p-2 text-sm"
                value={poText}
                onChange={(e) => setPoText(e.target.value)}
                placeholder="/api/parse で抽出したテキストが入ります"
              />
            </div>
            <div>
              <div className="mb-1 text-sm font-medium">該非判定書テキスト</div>
              <textarea
                className="w-full h-40 rounded-lg border p-2 text-sm"
                value={hiteiText}
                onChange={(e) => setHiteiText(e.target.value)}
                placeholder="/api/parse または /api/hitei-dedupe の結果"
              />
            </div>
            <div>
              <div className="mb-1 text-sm font-medium">修正指示（任意）</div>
              <textarea
                className="w-full h-24 rounded-lg border p-2 text-sm"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="例: 品目名は英字表記に統一、数量は整数に丸める など"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={doGenerate}
                disabled={generateBusy}
                className="rounded-lg bg-blue-600 text-white px-4 py-2 text-sm disabled:opacity-50"
              >
                {generateBusy ? "生成中..." : "JSONドラフト生成"}
              </button>
              <button
                onClick={doDiff}
                className="rounded-lg border px-3 py-2 text-sm hover:bg-gray-100"
              >
                差分を表示
              </button>
            </div>
          </div>
        </section>

        {/* RIGHT: Results & Diff */}
        <section className="space-y-4">
          <div className="rounded-2xl border bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-3">
              <div className="text-sm font-semibold">現在のJSON（手動編集可）</div>
              <button
                onClick={() => {
                  try {
                    const text = prettyDraft || "{}";
                    const obj = JSON.parse(text);
                    setCurrentJson(obj);
                    setCurrentText(JSON.stringify(obj, null, 2));
                  } catch {
                    // 生成が空/壊れている場合は何もしない
                  }
                }}
                className="ml-auto rounded-lg border px-3 py-1.5 text-xs hover:bg-gray-100"
              >
                ← ドラフトを反映
              </button>
            </div>

            {/* 編集用テキスト（ここは JSON 文字列として扱う） */}
            <textarea
              className="w-full h-48 rounded-lg border p-2 text-xs font-mono"
              value={currentText}
              onChange={(e) => setCurrentText(e.target.value)}
              onBlur={() => {
                try {
                  setCurrentJson(JSON.parse(currentText));
                } catch {
                  // JSON として不正な間は currentJson を更新しない
                }
              }}
              placeholder='{\n  "example": true\n}'
            />
          </div>

          <div className="rounded-2xl border bg-white p-4 shadow-sm">
            <div className="mb-2 text-sm font-semibold">生成されたJSONドラフト</div>
            <pre className="w-full h-48 overflow-auto rounded-lg border bg-gray-50 p-3 text-xs font-mono whitespace-pre-wrap">
{prettyDraft || "(未生成)"}
            </pre>
          </div>

          <div className="rounded-2xl border bg-white p-4 shadow-sm">
            <div className="mb-2 text-sm font-semibold">差分 (unified diff)</div>
            <pre className="w-full h-48 overflow-auto rounded-lg border bg-gray-50 p-3 text-xs font-mono whitespace-pre-wrap">
{diffText || "(差分なし)"}
            </pre>
          </div>
          
          {/* ---- JSX (画面表示部分) ---- */}
          <div className="flex items-center gap-3">
            <button onClick={doGenerate}>JSON生成</button>
            <button onClick={doDiff}>差分表示</button>

            {/* ✅ ここで downloadExcel を呼び出す */}
            <button onClick={() => downloadExcel(true)}>Excel出力（ドラフト）</button>
            <button onClick={() => downloadExcel(false)}>Excel出力（現在）</button>
          </div>

          {/* <div className="rounded-2xl border bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-3">
              <div className="text-sm font-semibold">tree.txt（任意）</div>
              <button
                onClick={loadTree}
                className="ml-auto rounded-lg border px-3 py-1.5 text-xs hover:bg-gray-100"
              >
                取得
              </button>
            </div>
            <pre className="w-full h-40 overflow-auto rounded-lg border bg-gray-50 p-3 text-xs font-mono whitespace-pre-wrap">
{tree || "(なし)"}
            </pre>
          </div> */}
        </section>
      </main>

      <footer className="mx-auto max-w-7xl p-4 text-xs text-gray-500">
        API Base: {apiBase}
      </footer>
    </div>
  );
}
