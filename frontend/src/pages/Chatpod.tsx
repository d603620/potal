import React, { useEffect, useRef, useState } from "react";

type Role = "user" | "assistant";

interface ChatMessage {
  role: Role;
  content: string;
}

const Chatpod: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>("");
  const [streaming, setStreaming] = useState<boolean>(false);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);

  // ▼ 追加：ドラッグ & ドロップ関連
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  // セッション作成
  useEffect(() => {
    void createNewSession();
  }, []);

  // 自動スクロール
  useEffect(() => {
    if (autoScroll) {
      endRef.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [messages, streaming, autoScroll]);

  const handleScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAutoScroll(distance < 80);
  };

  const createNewSession = async () => {
    try {
      const resp = await fetch("/api/session", { method: "POST" });
      if (!resp.ok) {
        console.error("Failed to create session", resp.status);
        return;
      }
      const json: { session_id?: string } = await resp.json();
      setSessionId(json.session_id ?? null);
      setMessages([]);
      setFiles([]);       // ★ アップロード済みファイルの表示をクリア
      setInput("");       // （お好みで）入力欄もクリア
    } catch (e) {
      console.error("Failed to create session", e);
    }
  };

  const clearHistory = async () => {
    await createNewSession();
  };

  // ▼ 追加：ファイルアップロード処理
  const uploadFiles = async (targetFiles: File[]) => {
    if (!sessionId) {
      console.error("no session_id");
      return;
    }

    for (const f of targetFiles) {
      const form = new FormData();
      form.append("session_id", sessionId); // ← ここ重要！名前も backend と合わせる
      form.append("file", f);               // ← backend の file: UploadFile = File(...)

      try {
        const resp = await fetch("/api/upload", {
          method: "POST",
          body: form,            // ← FormData をそのまま渡す（headers いじらない）
        });

        if (!resp.ok) {
          console.error("upload failed", resp.status);
          continue;
        }

        const json: {
          filename?: string;
          preview?: string;
          chars_total?: number;
          chars_used_in_context?: number;
        } = await resp.json();

        // UI側の表示（お好みで）
        const infoLine =
          `${json.filename ?? f.name} を読み込みました` +
          (json.chars_total != null
            ? `（約 ${json.chars_total} 文字 / コンテキストには ${json.chars_used_in_context ?? json.chars_total} 文字まで）`
            : "");

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              infoLine +
              (json.preview ? `\n\nプレビュー:\n${json.preview}` : ""),
          },
        ]);
      } catch (e) {
        console.error("upload error", e);
      }
    }
  };


  // ▼ 追加：ドラッグイベント
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const dt = e.dataTransfer;
    if (!dt?.files?.length) return;

    const droppedFiles = Array.from(dt.files);
    setFiles((prev) => [...prev, ...droppedFiles]);

    await uploadFiles(droppedFiles);
  };

  const handleFileInputChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const selectedFiles = e.target.files ? Array.from(e.target.files) : [];
    if (!selectedFiles.length) return;

    setFiles((prev) => [...prev, ...selectedFiles]);
    await uploadFiles(selectedFiles);
  };

  // ▼ 送信処理（既存）
  const send = async () => {
    if (!input.trim() || streaming || !sessionId) return;

    const userText = input.trim();
    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: userText },
      { role: "assistant", content: "" },
    ];

    setMessages(nextMessages);
    setInput("");
    setStreaming(true);
    setAutoScroll(true);

    requestAnimationFrame(() => {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          user_text: userText,
        }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        console.error("Chat request failed", resp.status);
        setStreaming(false);
        return;
      }

      const aiIndex = nextMessages.length - 1;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (!value) continue;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const p of parts) {
          if (!p.startsWith("data:")) continue;
          const data = p.slice(5).trim();
          if (data === "[DONE]") continue;

          try {
            const json = JSON.parse(data);

            if (json.error) {
              setMessages((prev) => {
                const copy = [...prev];
                const current = copy[aiIndex];
                if (!current) return prev;
                copy[aiIndex] = {
                  ...current,
                  content:
                    (current.content ? current.content + "\n" : "") +
                    `[error] ${json.error}`,
                };
                return copy;
              });
              continue;
            }

            const delta: string =
              json?.choices?.[0]?.delta?.content ?? "";

            if (delta) {
              setMessages((prev) => {
                const copy = [...prev];
                const current = copy[aiIndex];
                if (!current) return prev;
                copy[aiIndex] = {
                  ...current,
                  content: current.content + delta,
                };
                return copy;
              });
            }
          } catch {
            // パース失敗は無視
          }
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        console.info("Streaming aborted");
      } else {
        console.error("Chat request error", e);
      }
    } finally {
      setStreaming(false);
    }
  };

  const stop = () => {
    abortRef.current?.abort();
    setStreaming(false);
  };

  return (
    <div className="flex flex-col gap-4 max-w-6xl mx-auto">
      {/* ページヘッダー */}
      <div className="flex items-end justify-between mt-2">
        <div>
          <h2 className="text-2xl font-semibold text-white">DENG1 ChatBot</h2>
          <p className="text-sm text-white/70 mt-1">
            文書確認や問い合わせ対応を支援する社内向けAIチャット
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-white/70 mb-1">セッションID</div>
          <code className="text-xs px-3 py-1 rounded bg-white/10 text-white">
            {sessionId || "---"}
          </code>
        </div>
      </div>

      {/* メインカード */}
      <section
        className={`
          bg-white rounded-xl shadow-lg
          w-full max-w-6xl mx-auto
          flex flex-col
          h-[65vh] min-h-[480px]
        `}
      >
        {/* ツールバー */}
        <div className="flex items-center justify-between border-b px-5 py-3 bg-slate-50 rounded-t-xl">
          <div className="flex items-center gap-3">
            <button
              onClick={clearHistory}
              disabled={!sessionId || streaming}
              className="text-sm px-4 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-50"
            >
              履歴クリア
            </button>
          </div>
          <div className="text-xs text-slate-500 flex items-center gap-2">
            {streaming ? (
              <span className="inline-flex items-center gap-2 text-[#005BAC]">
                <span className="w-2 h-2 rounded-full bg-[#005BAC] animate-pulse" />
                応答生成中…
              </span>
            ) : (
              <span>Enterで送信 / Shift+Enterで改行</span>
            )}
          </div>
        </div>

        {/* メッセージリスト */}
        <div
          ref={listRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-5 py-4 bg-slate-50 space-y-3"
        >
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">
              右下の入力欄から、確認したい内容や質問を入力してください。
            </div>
          ) : (
            messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${
                  m.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                    m.role === "user"
                      ? "bg-[#005BAC] text-white rounded-br-md"
                      : "bg-white text-slate-800 border border-slate-200 rounded-bl-md"
                  }`}
                >
                  <div className="text-[10px] mb-1 opacity-70">
                    {m.role === "user" ? "You" : "AI"}
                  </div>
                  <div>{m.content || "..."}</div>
                </div>
              </div>
            ))
          )}
          <div ref={endRef} />
        </div>

        {/* ▼▼ 入力エリア（ドラッグ＆ドロップ対応版） ▼▼ */}
        <div
          className={`
            border-t px-5 py-3 rounded-b-xl
            ${isDragging ? "bg-sky-50 border-sky-300" : "bg-white"}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isDragging && (
            <div className="mb-2 text-xs text-sky-700">
              ここにファイルをドロップするとアップロードされます
            </div>
          )}

          {files.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2 text-xs text-slate-600">
              {files.map((f, idx) => (
                <span
                  key={`${f.name}-${idx}`}
                  className="px-2 py-1 rounded-full bg-slate-100 border border-slate-200"
                >
                  {f.name}
                </span>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm resize-none min-h-[80px] max-h-[160px] focus:outline-none focus:border-[#005BAC] focus:ring-1 focus:ring-[#005BAC]"
              placeholder="テキストを入力するか、ファイルをドラッグ＆ドロップしてください。"
            />

            <div className="flex items-center justify-between gap-3">

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs px-3 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:bg-slate-100"
                >
                  ファイルを選択
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileInputChange}
                />

                <div className="text-xs text-slate-400">
                  自動スクロール：{autoScroll ? "ON" : "OFF（手動スクロール中）"}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={stop}
                  disabled={!streaming}
                  className="text-xs px-3 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                >
                  停止
                </button>
                <button
                  onClick={() => void send()}
                  disabled={streaming || !sessionId || !input.trim()}
                  className="text-sm px-5 py-1.5 rounded-full bg-[#005BAC] text-white hover:bg-[#003E7E] disabled:opacity-50"
                >
                  送信
                </button>
              </div>

            </div>
          </div>
        </div>
        {/* ▲▲ 入力エリアここまで ▲▲ */}
      </section>
    </div>
  );
};

export default Chatpod;
