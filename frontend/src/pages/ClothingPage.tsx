import React, { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

type PopRow = { day: "today" | "tomorrow"; slot: string; pop: number | null };

type WeatherSummaryResponse = {
  pref_name: string;
  office_code: string;
  data: any;
  summary: string;
  pop_rows: PopRow[];
  max_pop_today: number | null;
  max_pop_tomorrow: number | null;
  icon_today: string | null;
  icon_tomorrow: string | null;
};

type ClothingAdviceResponse = { markdown: string };

export default function ClothingPage() {
  // Step1: inputs
  const [destination, setDestination] = useState("");
  const [origin, setOrigin] = useState("");

  // Step2: results
  const [wx, setWx] = useState<WeatherSummaryResponse | null>(null);
  const [wxLoading, setWxLoading] = useState(false);
  const [wxError, setWxError] = useState<string | null>(null);

  // Step3: clothing advice (quick + full)
  const [adviceQuick, setAdviceQuick] = useState<string>("");
  const [adviceFull, setAdviceFull] = useState<string>("");
  const [adviceLoading, setAdviceLoading] = useState(false);

  const mapsUrl = useMemo(() => {
    if (!origin.trim() || !destination.trim()) return "";
    const u = new URL("https://www.google.com/maps/dir/");
    u.searchParams.set("api", "1");
    u.searchParams.set("origin", origin);
    u.searchParams.set("destination", destination);
    u.searchParams.set("travelmode", "driving");
    return u.toString();
  }, [origin, destination]);

  const runWeather = async () => {
    setWxLoading(true);
    setWxError(null);
    setWx(null);
    setAdviceQuick("");
    setAdviceFull("");

    try {
      const res = await fetch("/api/weather/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destination }),
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `Weather API error: ${res.status}`);
      }

      const json = (await res.json()) as WeatherSummaryResponse;
      setWx(json);

      // Quick clothing advice (rule-based): use_azure=false
      const advRes = await fetch("/api/clothing/advice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pref_name: json.pref_name,
          data: json.data,
          use_azure: false,
        }),
      });
      if (advRes.ok) {
        const adv = (await advRes.json()) as ClothingAdviceResponse;
        setAdviceQuick(adv.markdown ?? "");
      }
    } catch (e: any) {
      setWxError(e?.message ?? "unknown error");
    } finally {
      setWxLoading(false);
    }
  };

  const runAdviceFull = async () => {
    if (!wx) return;
    setAdviceLoading(true);
    try {
      const advRes = await fetch("/api/clothing/advice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pref_name: wx.pref_name,
          data: wx.data,
          use_azure: true,
        }),
      });
      if (!advRes.ok) throw new Error(`Advice API error: ${advRes.status}`);
      const adv = (await advRes.json()) as ClothingAdviceResponse;
      setAdviceFull(adv.markdown ?? "");
    } catch (e: any) {
      setAdviceFull("");
      alert(e?.message ?? "自然文版の生成に失敗しました");
    } finally {
      setAdviceLoading(false);
    }
  };

  const canRunWeather = destination.trim().length > 0 && !wxLoading;
  const canOpenMaps = mapsUrl.length > 0;
  const canRunAdviceFull = !adviceLoading;

  return (
    <div className="dnp-page clothing-page">
      {/* Hero */}
      <div className="dnp-card clothing-hero">
        <div>
          <div className="dnp-page-eyebrow">WEATHER × AI</div>
          <h1 className="clothing-title">🌞 どこにお出かけしますか？</h1>
          <p className="clothing-subtitle">
             行き先に応じて天気を要約し、降水確率ピークと服装アドバイスを表示します。
          </p>
        </div>
      </div>

          {/* Step1: inputs + explicit run button */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
        <input
          className="
            h-12 flex-1
            rounded-[10px]
            bg-white text-slate-900
            border border-black/15
            px-4
            shadow-sm
            placeholder:text-slate-500/70
            focus:outline-none focus:ring-4 focus:ring-white/20 focus:border-white/60
          "
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          placeholder="行き先（例：東京、札幌、沖縄、横浜など）"
        />

        <button
          className="btn btn-primary h-12 rounded-full px-5"
          onClick={runWeather}
          disabled={!canRunWeather}
        >
          {wxLoading ? "取得中…" : "🔎 天気を取得する"}
        </button>
      </div>

      {wxError && (
        <div className="border rounded p-3 bg-red-50 text-red-800">
          {wxError}
        </div>
      )}


      {/* Step2: show summary + POP visualization */}
      {wx && (
        <div className="space-y-4">
          <div className="border rounded-2xl p-4 bg-white shadow-sm space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold">
                ☁ {wx.pref_name} の天気概要（AI要約）
              </h2>
              <div className="text-xs text-gray-500">office: {wx.office_code}</div>
            </div>
            <div className="whitespace-pre-wrap leading-relaxed">{wx.summary}</div>
          </div>

          <div className="border rounded-2xl p-4 bg-white shadow-sm space-y-3">
            <h3 className="text-lg font-semibold">☔ 降水確率ピーク（時間帯別）</h3>

            <div className="flex gap-3 flex-wrap">
              <div className="border rounded px-3 py-2">
                <div className="text-xs text-gray-500">今日の最大</div>
                <div className="text-lg font-semibold">
                  {wx.max_pop_today == null ? "—" : `${wx.max_pop_today}%`}
                </div>
              </div>
              <div className="border rounded px-3 py-2">
                <div className="text-xs text-gray-500">明日の最大</div>
                <div className="text-lg font-semibold">
                  {wx.max_pop_tomorrow == null ? "—" : `${wx.max_pop_tomorrow}%`}
                </div>
              </div>
            </div>

            <div className="overflow-auto">
              <table className="min-w-full border text-sm">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="border px-2 py-1">区分</th>
                    <th className="border px-2 py-1">時間帯</th>
                    <th className="border px-2 py-1">降水確率(%)</th>
                  </tr>
                </thead>
                <tbody>
                  {wx.pop_rows.map((r, i) => (
                    <tr key={i}>
                      <td className="border px-2 py-1">
                        {r.day === "today" ? "今日" : "明日"}
                      </td>
                      <td className="border px-2 py-1">{r.slot}</td>
                      <td className="border px-2 py-1">{r.pop == null ? "—" : r.pop}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Step3: route */}
          <div className="border rounded-2xl p-4 bg-white shadow-sm space-y-2">
            <h3 className="text-lg font-semibold">🗺️ 経路検索</h3>
            <div className="flex flex-col gap-2 md:flex-row md:items-center">
              <input
                className="border rounded px-3 py-2 flex-1"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="出発地（例：新宿駅、自宅など）"
              />
              <a
                className={[
                  "btn btn-outline",
                  canOpenMaps ? "" : "pointer-events-none opacity-60",
                ].join(" ")}
                href={canOpenMaps ? mapsUrl : "#"}
                target="_blank"
                rel="noreferrer"
                aria-disabled={!canOpenMaps}
              >
                🚗 Google Mapで経路を表示
              </a>
            </div>
            <div className="text-xs text-gray-500">クリックで別タブが開きます。</div>
          </div>

          {/* Step4: clothing advice quick + full */}
          <div className="border rounded-2xl p-4 bg-white shadow-sm space-y-3">
            <h3 className="text-lg font-semibold">👕 服装アドバイス</h3>

            {adviceQuick ? (
              <div className="prose max-w-none">
                <div className="text-sm text-gray-600 mb-2">
                  まずは簡易アドバイス（ルールベース）です。必要なら下で自然文版（Azure）を生成できます。
                </div>
                <ReactMarkdown>{adviceQuick}</ReactMarkdown>
              </div>
            ) : (
              <div className="text-sm text-gray-500">（簡易アドバイスを生成中/未生成）</div>
            )}

            <button
              className="btn btn-primary"
              onClick={runAdviceFull}
              disabled={!canRunAdviceFull}
            >
              {adviceLoading ? "生成中…" : "✨ 自然な文章で整える（Azure）"}
            </button>

            {adviceFull && (
              <div className="prose max-w-none">
                <h4>服装アドバイス（自然文版）</h4>
                <ReactMarkdown>{adviceFull}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}

      {!wx && !wxLoading && !wxError && (
        <div className="text-sm text-gray-500">
          行き先を入力して「天気を取得する」を押してください。
        </div>
      )}
    </div>
  );
}
