# backend/app/routers/kpi_analyzer.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core import kpi_analyzer_core as core
from openai import APIError, NotFoundError, BadRequestError, RateLimitError, APITimeoutError

router = APIRouter(prefix="/kpi", tags=["kpi"])

@router.post("/analyze")
async def analyze_kpi(file: UploadFile = File(...)):
    """CSVを受け取り、KPIとグラフデータ、要因説明を返す"""
    try:
        content = await file.read()
        df = core.load_csv(content)
        kpis = core.calc_kpis(df)
        chart_data = core.build_chart_data(df)

        # KPIサマリーを文字列にまとめる（9_の要約部分を流用）
        summary_text = (
    f"【最新 vs 1週間前の比較】\n"
    f"利益: {kpis['profit_latest']} 円 （差分: {kpis['profit_diff']} 円）\n"
    f"生産量(throughput): {kpis['throughput_latest']} （差分: {kpis['throughput_diff']}）\n"
    f"稼働率: {kpis['uptime_rate_latest']}% （差分: {kpis['uptime_rate_diff']}）\n"
    f"不良率: {kpis['defect_latest']}% （差分: {kpis['defect_diff']}）\n"
    f"ダウンタイム: {kpis['downtime_latest']} 分 （差分: {kpis['downtime_diff']} 分）\n"
    f"エネルギー消費: {kpis['energy_latest']} kWh （差分: {kpis['energy_diff']} kWh）\n"
)
        try:
            reason = core.call_azure_reasoning(summary_text)

        except NotFoundError as e:
            # 例: deployment名違い / endpoint / api_version不整合 など
            raise HTTPException(
                status_code=404,
                detail=f"Azure OpenAI resource not found: {e}"
            )

        except BadRequestError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Azure OpenAI bad request: {e}"
            )

        except RateLimitError as e:
            raise HTTPException(
                status_code=429,
                detail=f"Azure OpenAI rate limit: {e}"
            )

        except APITimeoutError as e:
            raise HTTPException(
                status_code=504,
                detail=f"Azure OpenAI timeout: {e}"
            )

        except APIError as e:
            # Azure側5xx等は 502 に寄せるのが分かりやすい
            raise HTTPException(
                status_code=502,
                detail=f"Azure OpenAI upstream error: {e}"
            )



        return {
            "kpis": kpis,
            "chart": chart_data,
            "reasoning": reason,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        # ログに詳細を書いて、フロントにはざっくり
        #raise HTTPException(status_code=500, detail="KPI分析中にエラーが発生しました。")
        raise HTTPException(status_code=500, detail=str(e))

    
