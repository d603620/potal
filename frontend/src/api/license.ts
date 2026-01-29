// src/api/license.ts

export type CommercialFlag = "allowed" | "restricted" | "prohibited" | "unknown";
export type UsageType = "internal" | "product" | "saas" | "redistribution";
export type JudgeLevel = "ok" | "conditional" | "ng" | "unknown";

export interface LicenseSummary {
  commercial_use: "allowed" | "restricted" | "prohibited" | "unknown";
  redistribution: "allowed" | "restricted" | "prohibited" | "unknown";
  modification: "allowed" | "restricted" | "prohibited" | "unknown";
  credit_required: boolean;
  copyleft: boolean;
  license_cost: "free" | "paid" | "mixed" | "unknown"; // ★追加
  key_conditions: string[];
  risk_points: string[];
}


export interface LicenseSummaryRequest {
  software_name?: string | null;
  license_text: string;
}

export interface LicenseSummaryResponse {
  summary: LicenseSummary;
  raw_output: string;
}

export interface LicenseJudgeRequest {
  software_name?: string | null;
  usage_type: UsageType;
  license_summary: LicenseSummary;
}

export interface LicenseJudgeResult {
  is_allowed: boolean;
  level: JudgeLevel;
  reasons: string[];
  conditions: string[];
}

export interface LicenseJudgeResponse {
  result: LicenseJudgeResult;
  raw_output: string;
}

// バックエンドのURL（必要に応じて .env などに逃がしてください）
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} - ${text}`);
  }
  return (await res.json()) as T;
}

export async function fetchLicenseSummary(
  body: LicenseSummaryRequest
): Promise<LicenseSummaryResponse> {
  const res = await fetch(`/api/license/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<LicenseSummaryResponse>(res);
}

export async function fetchLicenseJudge(
  body: LicenseJudgeRequest
): Promise<LicenseJudgeResponse> {
  const res = await fetch(`/api/license/judge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<LicenseJudgeResponse>(res);
}
