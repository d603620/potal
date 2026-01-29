// src/pages/LicenseCheckerPage.tsx

import { useState } from "react";
import {
  fetchLicenseSummary,
  fetchLicenseJudge,
  LicenseSummaryRequest,
  LicenseJudgeRequest,
  LicenseSummaryResponse,
  LicenseJudgeResponse,
  UsageType,
  LicenseSummary,
} from "../api/license";

// ----------------------------------------------------
// テキスト中の URL を a タグに変換するヘルパー
// ----------------------------------------------------
const urlPattern = /(https?:\/\/[^\s]+)/g;

function renderTextWithLinks(text: string) {
  const parts = text.split(urlPattern);

  return parts.map((part, index) => {
    // URL 部分だけ <a> にする
    if (part.match(urlPattern)) {
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
        >
          {part}
        </a>
      );
    }

    // それ以外はただのテキスト
    return <span key={index}>{part}</span>;
  });
}


// ----------------------------------------------------
// 翻訳ヘルパー
// ----------------------------------------------------

async function translateToJapanese(text: string): Promise<string> {
  if (!text.trim()) return text;

  try {
    const res = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        target_lang: "JA",
      }),
    });

    if (!res.ok) {
      console.warn("翻訳APIエラー", res.status);
      return text;
    }

    const data = await res.json();
    return data.translated_text ?? text;
  } catch (e) {
    console.error("翻訳API呼び出し失敗", e);
    return text;
  }
}

async function translateListToJa(list: string[]): Promise<string[]> {
  if (!list || list.length === 0) return list;

  // 一度に翻訳（行区切り）
  const joined = list.join("\n");
  const translated = await translateToJapanese(joined);
  return translated.split("\n");
}

// ----------------------------------------------------
// ページコンポーネント
// ----------------------------------------------------

type Phase = "idle" | "summarizing" | "judging";

const usageTypeOptions: { value: UsageType; label: string }[] = [
  { value: "internal", label: "社内利用のみ" },
  { value: "product", label: "製品に組み込み販売" },
  { value: "saas", label: "SaaSとして提供" },
  { value: "redistribution", label: "再配布（OSS配布など）" },
];

export default function LicenseCheckerPage() {
  const [softwareName, setSoftwareName] = useState("");
  const [licenseText, setLicenseText] = useState("");
  const [usageType, setUsageType] = useState<UsageType>("internal");

  const [phase, setPhase] = useState<Phase>("idle");
  const [summaryRes, setSummaryRes] = useState<LicenseSummaryResponse | null>(
    null
  );
  const [judgeRes, setJudgeRes] = useState<LicenseJudgeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ----------------------------------------------------
  // チェック実行
  // ----------------------------------------------------

  const runCheck = async () => {
    setError(null);
    setSummaryRes(null);
    setJudgeRes(null);

    //if (!licenseText.trim()) {
    //  setError("ライセンステキストを入力してください。");
    //  return;
    //}

    try {
      // --- 要約（英語） ---
      setPhase("summarizing");
      const summaryReq: LicenseSummaryRequest = {
        software_name: softwareName || null,
        license_text: licenseText,
      };
      const res1 = await fetchLicenseSummary(summaryReq);

      setSummaryRes(res1);

      // --- 判定（英語 summary を渡す必要あり） ---
      setPhase("judging");
      const judgeReq: LicenseJudgeRequest = {
        software_name: softwareName || null,
        usage_type: usageType,
        license_summary: res1.summary,
      };
      const res2 = await fetchLicenseJudge(judgeReq);

      setJudgeRes(res2);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setPhase("idle");
    }
  };

  // ----------------------------------------------------
  // ラベル変換
  // ----------------------------------------------------

  const labelFlag = (flag: LicenseSummary["commercial_use"]) => {
    switch (flag) {
      case "allowed":
        return "許可";
      case "restricted":
        return "条件付き";
      case "prohibited":
        return "禁止";
      default:
        return "不明";
    }
  };

  const labelLevel = (level: string) => {
    switch (level) {
      case "ok":
        return "OK（問題なし）";
      case "conditional":
        return "条件付きOK";
      case "ng":
        return "NG";
      default:
        return "不明";
    }
  };

  const labelCost = (cost: LicenseSummary["license_cost"]) => {
  switch (cost) {
    case "free":
      return "無償";
    case "paid":
      return "有償";
    case "mixed":
      return "条件により有償/無償";
    default:
      return "不明";
  }
};

  // ----------------------------------------------------
  // JSX
  // ----------------------------------------------------

  return (
    <div className="dnp-page">
      {/* 入力フォームカード */}
      <section className="dnp-card">
        <div className="dnp-page-eyebrow">LICENSE CHECKER</div>
        <h1 className="dnp-section-title">
          ソフトウェアライセンス 商用利用チェック
        </h1>
        <p className="dnp-page-subtitle">
          OSS ライセンス本文を貼り付けると、商用利用の可否や注意点を要約して表示します。
        </p>

        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <div className="dnp-field-label">ソフトウェア名（任意）</div>
            <input
              className="dnp-text-input"
              value={softwareName}
              onChange={(e) => setSoftwareName(e.target.value)}
              placeholder="例: ExampleLib 1.2.3"
            />
          </div>

          <div>
            <div className="dnp-field-label">利用形態</div>
            <select
              className="dnp-text-input"
              value={usageType}
              onChange={(e) => setUsageType(e.target.value as UsageType)}
            >
              {usageTypeOptions.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="dnp-field-label">ライセンステキスト</div>
            <textarea
              className="dnp-text-input"
              style={{ fontFamily: "monospace", fontSize: 13, minHeight: 220 }}
              value={licenseText}
              onChange={(e) => setLicenseText(e.target.value)}
              placeholder="MIT / Apache-2.0 などのライセンス本文を貼り付けてください"
            />
          </div>

          <div>
            <button
              type="button"
              className="dnp-btn dnp-btn-primary"
              onClick={runCheck}
              disabled={phase !== "idle"}
            >
              {phase === "summarizing"
                ? "ライセンス要約中..."
                : phase === "judging"
                ? "商用利用可否 判定中..."
                : "要約＋商用利用判定を実行"}
            </button>
          </div>

          {error && <div className="edu-error">{error}</div>}
        </div>
      </section>

      {/* ---------------------------------------------------- */}
      {/* ライセンス要約 */}
      {/* ---------------------------------------------------- */}

      {summaryRes && (
        <section className="dnp-card">
          <h2 className="dnp-section-title">ライセンス要約</h2>

          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 13,
              marginTop: 8,
            }}
          >
            <tbody>
              <tr>
                <th style={{
                  width: "35%", borderBottom: "1px solid var(--border)",
                  textAlign: "left", padding: "4px 8px"
                }}>
                  商用利用
                </th>
                <td style={{
                  borderBottom: "1px solid var(--border)",
                  padding: "4px 8px"
                }}>
                  {labelFlag(summaryRes.summary.commercial_use)}
                </td>
              </tr>

              <tr>
                <th style={{
                  borderBottom: "1px solid var(--border)",
                  textAlign: "left", padding: "4px 8px"
                }}>
                  再配布
                </th>
                <td style={{
                  borderBottom: "1px solid var(--border)",
                  padding: "4px 8px"
                }}>
                  {labelFlag(summaryRes.summary.redistribution)}
                </td>
              </tr>

              <tr>
                <th style={{
                  borderBottom: "1px solid var(--border)",
                  textAlign: "left", padding: "4px 8px"
                }}>
                  改変
                </th>
                <td style={{
                  borderBottom: "1px solid var(--border)",
                  padding: "4px 8px"
                }}>
                  {labelFlag(summaryRes.summary.modification)}
                </td>
              </tr>

              <tr>
                <th style={{
                  borderBottom: "1px solid var(--border)",
                  textAlign: "left", padding: "4px 8px"
                }}>
                  著作権表示義務
                </th>
                <td style={{
                  borderBottom: "1px solid var(--border)",
                  padding: "4px 8px"
                }}>
                  {summaryRes.summary.credit_required ? "あり" : "なし / 不明"}
                </td>
              </tr>

              <tr>
                <th style={{
                  borderBottom: "1px solid var(--border)",
                  textAlign: "left", padding: "4px 8px"
                }}>
                  コピーレフト性
                </th>
                <td style={{
                  borderBottom: "1px solid var(--border)",
                  padding: "4px 8px"
                }}>
                  {summaryRes.summary.copyleft ? "あり" : "なし / 不明"}
                </td>
              </tr>

              <tr>
                <th
                  style={{
                    borderBottom: "1px solid var(--border)",
                    textAlign: "left",
                    padding: "4px 8px",
                  }}
                >
                  ライセンス費用（有償/無償）
                </th>
                <td
                  style={{
                    borderBottom: "1px solid var(--border)",
                    padding: "4px 8px",
                  }}
                >
                  {labelCost(summaryRes.summary.license_cost)}
                </td>
              </tr>

            </tbody>
          </table>

          <div style={{ marginTop: 12 }}>
            <h3 className="dnp-field-label">重要な条件</h3>
            {summaryRes.summary.key_conditions.length === 0 ? (
              <p className="dnp-page-subtitle">（なし）</p>
            ) : (
              <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                {summaryRes.summary.key_conditions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <h3 className="dnp-field-label">リスク・要注意点</h3>
            {summaryRes.summary.risk_points.length === 0 ? (
              <p className="dnp-page-subtitle">（なし）</p>
            ) : (
              <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                {summaryRes.summary.risk_points.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {/* ---------------------------------------------------- */}
      {/* 商用利用判定 */}
      {/* ---------------------------------------------------- */}

      {judgeRes && (
        <section className="dnp-card">
          <h2 className="dnp-section-title">商用利用の判定</h2>

          <p style={{ fontSize: 14, marginTop: 4 }}>
            <strong>総合判定：</strong>
            {labelLevel(judgeRes.result.level)}（
            {judgeRes.result.is_allowed
              ? "商用利用可（条件付き含む）"
              : "商用利用不可 / 要検討"}
            ）
          </p>

          <div style={{ marginTop: 12 }}>
            <h3 className="dnp-field-label">判定理由</h3>
            {judgeRes.result.reasons.length === 0 ? (
              <p className="dnp-page-subtitle">（なし）</p>
            ) : (
              <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                {judgeRes.result.reasons.map((r, i) => (
                  <li key={i}>{renderTextWithLinks(r)}</li>
                ))}
              </ul>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <h3 className="dnp-field-label">条件・留意事項</h3>
            {judgeRes.result.conditions.length === 0 ? (
              <p className="dnp-page-subtitle">（なし）</p>
            ) : (
              <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                {judgeRes.result.conditions.map((c, i) => (
                  <li key={i}>{renderTextWithLinks(c)}</li>
                ))}
              </ul>
            )}
          </div>

          <p
            style={{
              fontSize: 11,
              color: "var(--text-sub)",
              marginTop: 12,
            }}
          >
            ※ 本ツールは社内検討の補助用です。最終判断は担当部門が行ってください。
          </p>
        </section>
      )}
    </div>
  );
}
