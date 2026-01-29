export type OracleNlqRequest = {
  question: string;
  limit?: number;
};

export type OracleNlqResponse = {
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
};

export async function queryOracleNlq(req: OracleNlqRequest) {
  const res = await fetch("/api/oracle-nlq/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || "API error");
  }
  return (await res.json()) as OracleNlqResponse;
}
