import React from "react";
import { Link } from "react-router-dom";

type MenuItem = {
  title: string;
  description: string;
  link: string;
  tone?: "solid" | "outline";
};

const menuItems: MenuItem[] = [
  {
    title: "Chatbot",
    description: "AIチャットでリサーチや文書作成をサポートします。",
    link: "/chatpod",
    tone: "solid",
  },
  {
    title: "取引審査票作成ドラフト",
    description: "製品の発注書と該非判定書から輸出向け取引審査票ドラフトをexcelで作成します。",
    link: "/filejson",
    tone: "solid",
  },
    // ★ ここから追加！
  {
    title: "トラブル事例検索",
    description: "過去のトラブル事例を条件で検索し、暗黙知も確認できます。",
    link: "/trouble/search",
    tone: "solid",
  },
  {
    title: "暗黙知 承認",
    description: "現場から登録された暗黙知を承認し、ナレッジへ反映します。",
    link: "/trouble/tacit",
    tone: "solid",
  },
  {
  title: "経営指標分析（KPI）",
  description: "売上・利益などの経営指標をアップロードしたCSVから可視化・分析します。",
  link: "/kpi/analyzer",   // ← ここ
  tone: "solid",
  },
 {
    title: "教育資料作成デモ",
    description: "教育資料作成支援エージェントのデモ画面を表示します。",
    link: "/edu-demo",
    tone: "solid",
  }, 
  {
    title: "ライセンスチェッカーツール",
    description: "ソフトウェアライセンスの要約と商用利用可否判定を支援します。",
    link: "/license-checker",
    tone: "solid",
  },
  {
    title: "Oracle NLQ",
    description: "自然文での質問からSQLを生成し、Oracleデータベースに問い合わせます。",
    link: "/oracle-nlq",
    tone: "solid",  
  },
  {
    title: "ログイン画面へ",
    description: "ログイン画面に移動します。",
    link: "/login",
    tone: "outline",
  },
  {
    title: "プロフィール画面へ",
    description: "プロフィール画面に移動します。",
    link: "/profile",
    tone: "outline",  
  },
];


const Dashboard: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* タイトル＆概要エリア（DNPブルーのパネル） */}
      <section className="bg-[var(--dnp-blue)] text-[var(--dnp-text-light)] rounded-2xl shadow-lg px-6 py-5 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide opacity-80">
            Integrated Manufacturing Innovation Laboratory Internal Portal
          </p>
          <h1 className="text-2xl md:text-3xl font-bold mt-1">
            Dashboard
          </h1>
          <p className="text-sm mt-2 opacity-90">
            日々の業務でよく使う機能に、ここからすぐアクセスできます。
          </p>
        </div>
        <div className="mt-3 md:mt-0 text-sm md:text-right opacity-90">
          <p>本日の作業をスムーズに。</p>
          <p>Chatbot とツール群で業務をサポートします。</p>
        </div>
      </section>

      {/* 機能カードエリア */}
      <section>
        <h2 className="text-sm text-white font-semibold text-[var(--dnp-text-main)] mb-3">
          機能メニュー
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {menuItems.map((item) => {
            const isSolid = item.tone === "solid";

            return (
              <article
                key={item.title}
                className="rounded-2xl shadow-md border border-gray-100 overflow-hidden bg-white flex flex-col"
              >
                {/* カード上部の色帯（DNPブルー系） */}
                <div
                  className={
                    "h-1.5 w-full " +
                    (isSolid
                      ? "bg-[var(--dnp-blue)]"
                      : "bg-[var(--dnp-blue-dark)]/70")
                  }
                />

                <div className="p-5 flex flex-col flex-1 justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-[var(--dnp-blue-dark)] mb-1">
                      {item.title}
                    </h3>
                    <p className="text-sm text-gray-600">{item.description}</p>
                  </div>

                  <div className="mt-4 flex justify-end">
                    <Link
                      to={item.link}
                      className={
                        "inline-flex items-center text-sm font-medium rounded-full px-4 py-2 transition " +
                        (isSolid
                          ? "bg-[var(--dnp-blue)] text-white hover:bg-[var(--dnp-blue-dark)]"
                          : "border border-[var(--dnp-blue)] text-[var(--dnp-blue)] bg-white hover:bg-[var(--dnp-blue)] hover:text-white")
                      }
                    >
                      開く
                    </Link>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
