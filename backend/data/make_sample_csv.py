
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_dummy_trouble_db.py
---------------------------------
過去N年分のトラブルDBダミーデータを自動生成します。

Usage:
  python generate_dummy_trouble_db.py --n 50 --years 10 --out trouble_db.csv --seed 42
"""
import argparse
import random
from datetime import datetime, timedelta
import csv

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="生成件数")
    ap.add_argument("--years", type=int, default=10, help="さかのぼる年数")
    ap.add_argument("--out", type=str, default="trouble_db.csv", help="出力CSVパス")
    ap.add_argument("--seed", type=int, default=42, help="乱数シード（再現性）")
    return ap.parse_args()

def random_date(start, end, rnd):
    delta = end - start
    return start + timedelta(days=rnd.randint(0, delta.days))

def pick_tags(tags_pool, rnd):
    k = rnd.randint(2, 4)
    return ";".join(sorted(rnd.sample(tags_pool, k)))

def make_note(notes_pool, rnd):
    return rnd.choice(notes_pool)

def main():
    args = parse_args()
    rnd = random.Random(args.seed)

    today = datetime.today()
    start_date = today - timedelta(days=365 * args.years)

    titles_pool = [
        "印刷ムラ発生","色ブレ発生","版ズレ発生","用紙詰まり","ラミネート不良",
        "接着不良","コート層はがれ","異物混入","バーコード読取不良","表面傷",
        "納期遅延","数量不足","ラベル糊残り","静電気による付着","搬送ローラー滑り",
        "サーバ障害","DB接続枯渇","ネットワーク遅延","バックアップ失敗","監視アラート誤検知",
        "品質検査NG","寸法公差外れ","色差ΔE超過","UV硬化不良","乾燥不足"
    ]

    summary_frag = [
        "高湿度で紙の含水率が上昇し再現が不安定",
        "版の摩耗によりドット形状が崩れた",
        "温湿度が規定範囲外で乾燥が不十分",
        "夜間バッチが集中しCPUとIOが飽和",
        "溶剤の配合比が想定外に変動",
        "ライン速度上げ過ぎで硬化が追いつかず",
        "清掃手順の抜け漏れにより粉塵が混入",
        "搬送ローラーの摩耗により蛇行",
        "ICCプロファイル不整合で色差が拡大",
        "接着剤の塗布量が過少",
        "ラベル台紙との相性問題で剥離が不良",
        "ネットワーク機器のファーム不具合",
        "クラウドDBの接続上限に到達",
        "検査装置のキャリブレーション不備",
        "温調器のセンサドリフト"
    ]

    root_causes = [
        "用紙の湿度ムラ","版の摩耗","乾燥温度の設定ミス","接続プール設定不足","溶剤配合エラー",
        "ライン速度過多","清掃不備","ローラー摩耗","プロファイル不整合","塗布量不足",
        "材料相性不良","FWバグ","同時接続過多","キャリブレーション不備","センサドリフト",
        "作業手順逸脱","原材料ロット異常","温湿度管理不良","UV出力低下","冷却不足"
    ]

    countermeasures = [
        "用紙乾燥と湿度管理の強化","版交換と印圧調整","乾燥温度を規定値に再設定",
        "接続プール拡張とジョブ分散","配合手順の見直しと二重確認",
        "ライン速度を規格内へ調整","清掃手順の標準化とチェックリスト化",
        "ローラー交換と蛇行補正","ICCプロファイルの再作成","塗布ヘッドの点検と流量校正",
        "材料組み合わせの事前評価","FW更新とリブート手順整備","ピーク時のスケジュール平準化",
        "定期キャリブレーションの実施","センサ交換と校正","作業標準の再教育",
        "受入検査の強化","温湿度の自動監視","UVランプ交換","冷却風量の増強"
    ]

    products = ["ProductA","ProductB","ProductC","ProductD","ProductE"]
    clients = ["ClientA","ClientB","ClientC","ClientD","ClientE","ClientF","ClientG","ClientH"]
    tags_pool = ["印刷","色ムラ","版ズレ","搬送","ラミネート","接着","異物","検査","IT","DB","ネットワーク","品質","UV","乾燥","温湿度"]
    owners = ["製造1課","製造2課","品質保証","生産技術","資材調達","IT運用","保全チーム"]
    notes_pool = [
        "梅雨時は湿度センサのドリフトに注意",
        "夜間はジョブが集中するため閾値を厳しめに",
        "色交換直後は先頭10mは調整用として扱う",
        "週次の清掃でローラー端部の堆積を重点確認",
        "UVランプの使用時間をダッシュボードで監視",
        "材料ロット変更時は試し刷りを必須化"
    ]

    # 出力
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id","date","title","summary","root_cause","countermeasure",
                         "product","client","tags","severity","owner","lead_time_hours","tacit_notes"])

        for i in range(args.n):
            dt = random_date(start_date, today, rnd)
            row = {
                "id": f"A{str(i+1).zfill(3)}",
                "date": dt.strftime("%Y-%m-%d"),
                "title": rnd.choice(titles_pool),
                "summary": rnd.choice(summary_frag),
                "root_cause": rnd.choice(root_causes),
                "countermeasure": rnd.choice(countermeasures),
                "product": rnd.choice(products),
                "client": rnd.choice(clients),
                "tags": pick_tags(tags_pool, rnd),
                "severity": rnd.choices([1,2,3,4,5], weights=[10,20,35,25,10])[0],
                "owner": rnd.choice(owners),
                # lognormal-like (平均寄りに偏った右裾分布)
                "lead_time_hours": round(max(1.0, rnd.lognormvariate(2.0, 0.6)), 1),
                "tacit_notes": make_note(notes_pool, rnd)
            }
            writer.writerow([row[k] for k in ["id","date","title","summary","root_cause","countermeasure",
                                              "product","client","tags","severity","owner","lead_time_hours","tacit_notes"]])

    print(f"Generated {args.n} rows -> {args.out}")

if __name__ == "__main__":
    main()
