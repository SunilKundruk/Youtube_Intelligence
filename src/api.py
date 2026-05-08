from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import pandas as pd
import io
import os
from dotenv import load_dotenv

load_dotenv(override=True)

from src.data_processing import process_channel_data, process_video_data, validate_data_quality
from src.feature_engineering import engineer_channel_features, engineer_video_features
from src.forecasting import forecast_channel_growth, load_model
from src.insights import perform_weekend_analysis, generate_rule_based_insights, generate_genai_insights
from src.tracking import get_latest_metrics
from src.pipeline import run_ml_pipeline

app = FastAPI(title="TubePulse Growth & Revenue Intelligence API")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "YouTube Intelligence API is running."}

@app.get("/metrics")
def get_metrics(metric: str = "subscribers"):
    """Returns the latest accuracy metrics for a model."""
    metrics = get_latest_metrics(metric)
    if metrics:
        return {"status": "success", "data": metrics}
    return {"status": "error", "message": "No metrics found."}

@app.post("/retrain")
async def retrain_pipeline():
    """Triggers the full ML pipeline retraining."""
    success = run_ml_pipeline()
    if success:
        return {"status": "success", "message": "Pipeline completed and models updated."}
    return {"status": "error", "message": "Pipeline failed."}

@app.post("/analyze")
async def analyze_data(
    channel_file: UploadFile = File(...),
    video_file: UploadFile = File(None),
    cpm: float = Form(5.0),
    forecast_periods: int = Form(30)
):
    try:
        # Read files into pandas
        channel_content = await channel_file.read()
        channel_df = pd.read_csv(io.BytesIO(channel_content))
        
        video_df = None
        if video_file:
            video_content = await video_file.read()
            video_df = pd.read_csv(io.BytesIO(video_content))
            
        # 1. Validation
        validate_data_quality(channel_df, ['date', 'subscribers', 'total_views'])

        # 2. Processing
        channel_df = process_channel_data(channel_df)
        if video_df is not None:
            video_df = process_video_data(video_df)
            
        # 3. Feature Engineering
        channel_features = engineer_channel_features(channel_df, video_df)
            
        # 4. Forecasting (Handles Eval and Persistence internally now)
        results = forecast_channel_growth(channel_features, periods=forecast_periods, cpm=cpm)
        
        # 5. Insights
        weekend_analysis = perform_weekend_analysis(channel_features)
        rule_insights = generate_rule_based_insights(channel_features)
        
        metrics_summary = {
            "Total Subscribers": int(channel_features['subscribers'].iloc[-1]) if 'subscribers' in channel_features else None,
            "Total Views": int(channel_features['total_views'].iloc[-1]) if 'total_views' in channel_features else None,
            "Weekend Analysis": weekend_analysis,
            f"Projected {forecast_periods}-Day Revenue": results.get('projected_revenue', 0),
        }
        
        genai_insights = generate_genai_insights(str(metrics_summary))
        
        def df_to_dict(df):
            if df is None or df.empty:
                return []
            df_copy = df.copy()
            for col in df_copy.select_dtypes(include=['datetime64[ns]']).columns:
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d')
            return df_copy.to_dict(orient='records')
            
        response = {
            "status": "success",
            "data": {
                "channel_features": df_to_dict(channel_features),
                "weekend_analysis": weekend_analysis,
                "rule_insights": rule_insights,
                "genai_insights": genai_insights,
                "forecasts": {
                    "subscribers": df_to_dict(results['forecasts'].get('subscribers', pd.DataFrame())),
                    "total_views": df_to_dict(results['forecasts'].get('total_views', pd.DataFrame())),
                    "projected_revenue": results.get('projected_revenue', 0)
                },
                "accuracy_metrics": results.get('metrics', {})
            }
        }
        return response
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
