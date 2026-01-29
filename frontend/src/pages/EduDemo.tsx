// src/pages/EduDemo.tsx
import React, { useEffect, useRef, useState } from "react";

const API_BASE = "http://localhost:8000";

type Role = "user" | "assistant";

interface ScenarioItem {
  role: Role;
  text: string;
  file_name?: string;
  file_url?: string;   // ← 追加
}

type SpinnerType = "spinner" | "spinner_done";

interface Message extends ScenarioItem {
  type?: SpinnerType;
}

const SPINNER_STEPS = [2, 4];

const EduDemo: React.FC = () => {
  const [scenario, setScenario] = useState<ScenarioItem[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [paused, setPaused] = useState(false);
  const [spinnerStep, setSpinnerStep] = useState<number | null>(null);
  const [speedLabel, setSpeedLabel] = useState<"速い" | "普通" | "遅い">("普通");
  const [intervalMs, setIntervalMs] = useState(600);
  const [errorMessage, setErrorMessage] = useState<string | null>(null); // ← 追加
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // シナリオ取得
  useEffect(() => {
    const fetchScenario = async () => {
      const res = await fetch("/api/scenario");
      const data: { scenario: ScenarioItem[] } = await res.json();
      setScenario(data.scenario);
    };
    fetchScenario();
  }, []);

  // スクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 速度ラベル → ms
  useEffect(() => {
    if (speedLabel === "速い") setIntervalMs(300);
    else if (speedLabel === "普通") setIntervalMs(600);
    else setIntervalMs(1000);
  }, [speedLabel]);

const handleFileDownload = async (fileName: string, fileUrl: string) => {
  setErrorMessage(null);

  try {
    const res = await fetch(fileUrl);  // ← method: "HEAD" はやめて通常の GET

    if (!res.ok) {
      setErrorMessage("ファイルが見つかりませんでした。");
      return;
    }

    // ファイル本体を取得して、そのままダウンロードさせる
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);
  } catch (err) {
    setErrorMessage("ネットワークエラーが発生しました。");
  }
};

  // 再生ロジック
  useEffect(() => {
    if (!playing || paused) return;
    if (!scenario.length) return;

    // スピナー → 本カード
    if (spinnerStep !== null) {
      const realStep = spinnerStep;
      const item = scenario[realStep];

      setMessages(prev => {
        if (!prev.length) return prev;
        const cloned = [...prev];
        const last = cloned[cloned.length - 1];
        if (last.type === "spinner") {
          cloned[cloned.length - 1] = { ...last, type: "spinner_done" };
        }
        return cloned;
      });

      const timer = window.setTimeout(() => {
        setMessages(prev => [...prev, item]);
        setStep(realStep + 1);
        setSpinnerStep(null);
      }, 2000);

      return () => window.clearTimeout(timer);
    }

    if (step >= scenario.length) {
      setPlaying(false);
      setPaused(false);
      return;
    }

    const item = scenario[step];

    const timer = window.setTimeout(() => {
      if (item.file_name && SPINNER_STEPS.includes(step)) {
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            text: "資料を作成中です...",
            type: "spinner",
          },
        ]);
        setSpinnerStep(step);
      } else {
        setMessages(prev => [...prev, item]);
        setStep(s => s + 1);
      }
    }, intervalMs);

    return () => window.clearTimeout(timer);
  }, [playing, paused, step, spinnerStep, scenario, intervalMs]);

  const handlePlay = () => {
    setMessages([]);
    setStep(0);
    setPlaying(true);
    setPaused(false);
    setSpinnerStep(null);
    setErrorMessage(null);
  };

  const handlePause = () => setPaused(true);

  const handleResume = () => {
    setPaused(false);
    setPlaying(true);
  };

  const handleReset = () => {
    setMessages([]);
    setStep(0);
    setPlaying(false);
    setPaused(false);
    setSpinnerStep(null);
    setSpeedLabel("普通");
    setErrorMessage(null);
  };

  return (
    <div className="dnp-page">

      {/* ① ヒーローカード */}
      <div className="dnp-card edu-hero-card">
        <div className="edu-hero-left">
          <div className="dnp-page-eyebrow">TRAINING MATERIAL</div>
          <h1 className="dnp-page-title">教育資料作成支援エージェント（デモ）</h1>
          <p className="dnp-page-subtitle">
            取引法ガイドブックをもとにした社内向け勉強会資料作成の流れを再現します。
          </p>
        </div>
        <div className="edu-hero-right">
          発注担当者向け説明資料や案内メール用の短縮版、<br />
          関連マニュアルの改訂イメージを1画面で確認できます。
        </div>
      </div>

      {/* ② チャット / 制御パネル */}
      <div className="edu-layout-row">
        {/* 左：チャット */}
        <section className="dnp-card edu-chat-card">
          {messages.length === 0 && (
            <div className="edu-placeholder">
              「▶ 再生」を押すと、ここにAIとのやり取りが順番に表示されます。
            </div>
          )}

          <div className="edu-chat-scroll">
            {messages.map((m, i) => {
              const isUser = m.role === "user";
              const fileUrl =
                m.file_url ??
                `${API_BASE}/api/data/${encodeURIComponent(m.file_name ?? "")}`;

              return (
                <div
                  key={i}
                  className={`bubble ${isUser ? "user" : "ai"} edu-bubble`}
                >
                  <div className="bubble-role">
                    {isUser ? "ユーザー" : "AIアシスタント"}
                  </div>
                  <div className="bubble-text">{m.text}</div>

                  {m.type && (
                    <div
                      className={
                        "edu-spinner " +
                        (m.type === "spinner_done" ? "edu-spinner--done" : "")
                      }
                    >
                      <span className="edu-spinner__icon" />
                      <span className="edu-spinner__label">
                        {m.type === "spinner"
                          ? "資料を作成中です..."
                          : "資料が作成されました"}
                      </span>
                    </div>
                  )}

                  {/* ★ ダウンロードボタン */}
                  {m.file_name && !m.type && (
                    <div className="edu-file-link">
                      <button
                        className="edu-file-button"
                        onClick={() =>
                          handleFileDownload(m.file_name!, fileUrl)
                        }
                      >
                        📁 {m.file_name}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}

            {/* エラー表示 */}
            {errorMessage && (
              <div className="edu-error">{errorMessage}</div>
            )}

            <div ref={bottomRef} />
          </div>
        </section>

        {/* 右：制御パネル */}
        <aside className="dnp-card edu-side-card">
          <h2 className="dnp-section-title">再生制御</h2>
          <p className="dnp-section-caption">
            会話の流れを、説明用モニターなどに表示しながら操作できます。
          </p>

          <div className="dnp-field-label" style={{ marginTop: 8 }}>
            再生速度
          </div>
          <select
            className="dnp-text-input"
            value={speedLabel}
            onChange={e =>
              setSpeedLabel(e.target.value as "速い" | "普通" | "遅い")
            }
          >
            <option value="速い">速い</option>
            <option value="普通">普通</option>
            <option value="遅い">遅い</option>
          </select>

          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              type="button"
              className="dnp-btn dnp-btn-primary"
              onClick={handlePlay}
            >
              ▶ 再生
            </button>
            <button
              type="button"
              className="dnp-btn dnp-btn-outline"
              onClick={handlePause}
              disabled={!playing || paused}
            >
              ⏸ 一時停止
            </button>
            <button
              type="button"
              className="dnp-btn dnp-btn-subtle"
              onClick={handleResume}
              disabled={!paused || !scenario.length}
            >
              ▶ 再開
            </button>
          </div>

          <button
            type="button"
            className="dnp-btn dnp-btn-subtle"
            style={{ marginTop: 8 }}
            onClick={handleReset}
          >
            🔄 初期化（リセット）
          </button>

          <p className="dnp-section-caption" style={{ marginTop: 12 }}>
            ※本デモでは、実際のAI生成ではなく、事前に用意したPPTX/Wordファイルを
            ダウンロードボタンとして表示しています。
          </p>
        </aside>
      </div>
    </div>
  );
};

export default EduDemo;
