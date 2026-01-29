import React, { useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";

import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend
);

// バックエンドの kpi_analyzer_core.py に合わせた型
type KpiResponse = {
  kpis: {
    latest_date: string;
    prev_date: string;

    uptime_rate_latest: number;
    uptime_rate_diff: number;

    throughput_latest: number;
    throughput_diff: number;

    downtime_latest: number;
    downtime_diff: number;

    defect_latest: number;
    defect_diff: number;

    energy_latest: number;
    energy_diff: number;

    profit_latest: number;
    profit_diff: number;
  };
  chart: {
    dates: string[];
    series: {
      uptime_rate: number[];
      throughput_per_hr: number[];
      downtime_min: number[];
      defect_rate_pct: number[];
      energy_kwh: number[];
      profit_yen: number[];
    };
  };
  reasoning: string;
};

const KpiAnalyzerPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<KpiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setError(null);

    try {
      const res = await axios.post<KpiResponse>(
        // バックエンドの URL に合わせて調整してください
        "/api/kpi/analyze",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      setData(res.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ??
          "分析中にエラーが発生しました。CSVの形式を確認してください。"
      );
    } finally {
      setLoading(false);
    }
  };

  // データが無いときはグラフを描かない
  const labels = data?.chart?.dates ?? [];

  const profitChartData =
    data &&
    labels.length && {
      labels,
      datasets: [
        {
          label: "利益 (円)",
          data: data.chart.series.profit_yen,
          borderColor: "rgba(239, 68, 68, 1)", // 赤
          backgroundColor: "rgba(239, 68, 68, 0.2)",
          tension: 0.2,
        },
      ],
    };

  const throughputChartData =
    data &&
    labels.length && {
      labels,
      datasets: [
        {
          label: "スループット (/h)",
          data: data.chart.series.throughput_per_hr,
          borderColor: "rgba(59, 130, 246, 1)", // 青
          backgroundColor: "rgba(59, 130, 246, 0.2)",
          tension: 0.2,
        },
      ],
    };

  const uptimeChartData =
    data &&
    labels.length && {
      labels,
      datasets: [
        {
          label: "稼働率 (%)",
          data: data.chart.series.uptime_rate,
          borderColor: "rgba(34, 197, 94, 1)", // 緑
          backgroundColor: "rgba(34, 197, 94, 0.2)",
          tension: 0.2,
        },
      ],
    };

  const defectChartData =
    data &&
    labels.length && {
      labels,
      datasets: [
        {
          label: "不良率 (%)",
          data: data.chart.series.defect_rate_pct,
          borderColor: "rgba(234, 179, 8, 1)", // 黄
          backgroundColor: "rgba(234, 179, 8, 0.2)",
          tension: 0.2,
        },
      ],
    };

  const downtimeChartData =
    data &&
    labels.length && {
      labels,
      datasets: [
        {
          label: "ダウンタイム (分)",
          data: data.chart.series.downtime_min,
          borderColor: "rgba(107, 114, 128, 1)", // グレー
          backgroundColor: "rgba(107, 114, 128, 0.2)",
          tension: 0.2,
        },
      ],
    };

  const energyChartData =
    data &&
    labels.length && {
      labels,
      datasets: [
        {
          label: "エネルギー使用量 (kWh)",
          data: data.chart.series.energy_kwh,
          borderColor: "rgba(14, 116, 144, 1)", // ティール
          backgroundColor: "rgba(14, 116, 144, 0.2)",
          tension: 0.2,
        },
      ],
    };

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          boxWidth: 12,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 0,
        },
      },
    },
  } as const;

  return (
    <div className="space-y-8">
      {/* ヘッダーパネル */}
      <section className="bg-[var(--dnp-blue)] text-[var(--dnp-text-light)] rounded-2xl shadow-lg px-6 py-5 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide opacity-80">
            KPI Analyzer
          </p>
          <h1 className="text-2xl md:text-3xl font-bold mt-1">
            生産KPI分析（デモ）
          </h1>
          <p className="text-sm mt-2 opacity-90">
            date, uptime, throughput, downtime, defect, energy, profit の推移を分析します。
          </p>
        </div>
        <div className="mt-3 md:mt-0 text-sm md:text-right opacity-90">
          <p>CSVをアップロードして分析を開始してください。</p>
        </div>
      </section>

      {/* メインコンテンツ */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左：アップロード＋KPIサマリー */}
        <article className="lg:col-span-1 bg-white rounded-2xl shadow-md border border-gray-100 p-5 space-y-4">
          <h2 className="text-lg font-semibold text-[var(--dnp-blue-dark)]">
            データアップロード
          </h2>
          <p className="text-sm text-gray-600">
            列構成:
            <br />
            <code className="text-xs break-all">
              date, uptime_rate, throughput_per_hr, downtime_min,
              defect_rate_pct, energy_kwh, profit_yen
            </code>
          </p>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="block w-full text-sm mt-2"
          />

          {loading && (
            <p className="text-sm text-[var(--dnp-blue-dark)] mt-2">
              分析中です…
            </p>
          )}
          {error && (
            <p className="text-sm text-red-600 mt-2 whitespace-pre-line">
              {error}
            </p>
          )}

          {data && (
            <div className="mt-4 border-t border-gray-200 pt-4 space-y-2">
              <h3 className="text-sm font-semibold text-gray-800 mb-1">
                KPIサマリー（最新 vs 1週間前）
              </h3>
              <p className="text-xs text-gray-500">
                対象期間: {data.kpis.prev_date} → {data.kpis.latest_date}
              </p>
              <div className="text-xs text-gray-700 space-y-1">
                <p>
                  利益: {data.kpis.profit_latest.toLocaleString()} 円（差分:{" "}
                  {data.kpis.profit_diff >= 0 ? "＋" : ""}
                  {data.kpis.profit_diff.toLocaleString()} 円）
                </p>
                <p>
                  スループット: {data.kpis.throughput_latest.toFixed(2)} /h
                  （差分: {data.kpis.throughput_diff.toFixed(2)}）
                </p>
                <p>
                  稼働率: {data.kpis.uptime_rate_latest.toFixed(2)} %
                  （差分: {data.kpis.uptime_rate_diff.toFixed(2)} pt）
                </p>
                <p>
                  不良率: {data.kpis.defect_latest.toFixed(2)} %
                  （差分: {data.kpis.defect_diff.toFixed(2)} pt）
                </p>
                <p>
                  ダウンタイム: {data.kpis.downtime_latest.toFixed(1)} 分
                  （差分: {data.kpis.downtime_diff.toFixed(1)} 分）
                </p>
                <p>
                  エネルギー: {data.kpis.energy_latest.toFixed(1)} kWh
                  （差分: {data.kpis.energy_diff.toFixed(1)} kWh）
                </p>
              </div>
            </div>
          )}
        </article>

        {/* 右：グラフ＋要因分析 */}
        <article className="lg:col-span-2 bg-white rounded-2xl shadow-md border border-gray-100 p-5 space-y-4">
          <h2 className="text-lg font-semibold text-[var(--dnp-blue-dark)]">
            各KPIの推移グラフ &amp; 要因分析
          </h2>

          {data ? (
            <>
              {/* グラフ群 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="h-48 border border-gray-100 rounded-xl p-3">
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    利益 (円)
                  </p>
                  {profitChartData && (
                    <Line data={profitChartData} options={commonOptions} />
                  )}
                </div>
                <div className="h-48 border border-gray-100 rounded-xl p-3">
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    スループット (/h)
                  </p>
                  {throughputChartData && (
                    <Line data={throughputChartData} options={commonOptions} />
                  )}
                </div>
                <div className="h-48 border border-gray-100 rounded-xl p-3">
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    稼働率 (%)
                  </p>
                  {uptimeChartData && (
                    <Line data={uptimeChartData} options={commonOptions} />
                  )}
                </div>
                <div className="h-48 border border-gray-100 rounded-xl p-3">
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    不良率 (%)
                  </p>
                  {defectChartData && (
                    <Line data={defectChartData} options={commonOptions} />
                  )}
                </div>
                <div className="h-48 border border-gray-100 rounded-xl p-3">
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    ダウンタイム (分)
                  </p>
                  {downtimeChartData && (
                    <Line data={downtimeChartData} options={commonOptions} />
                  )}
                </div>
                <div className="h-48 border border-gray-100 rounded-xl p-3">
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    エネルギー使用量 (kWh)
                  </p>
                  {energyChartData && (
                    <Line data={energyChartData} options={commonOptions} />
                  )}
                </div>
              </div>

              {/* Azure コメント */}
              <div className="mt-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">
                  変動要因コメント（Azure）
                </h3>
                <p className="text-sm text-gray-700 whitespace-pre-line">
                  {data.reasoning}
                </p>
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500 mt-2">
              まだデータがありません。CSVをアップロードすると、ここにグラフとコメントが表示されます。
            </p>
          )}
        </article>
      </section>
    </div>
  );
};

export default KpiAnalyzerPage;
