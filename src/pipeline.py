import pandas as pd
import os
import sys
from datetime import datetime

# Add src to path if needed
sys.path.append(os.path.join(os.getcwd(), 'src'))

from data_processing import process_channel_data, process_video_data, validate_data_quality
from feature_engineering import engineer_channel_features, engineer_video_features
from forecasting import forecast_channel_growth
from tracking import start_mlflow_run, log_to_mlflow

def run_ml_pipeline():
    """
    Orchestrates the full ML Pipeline: Ingest -> Validate -> Process -> Train -> Evaluate -> Save -> Log.
    """
    print(f"[{datetime.now()}] Starting TubePulse ML Pipeline...")
    
    with start_mlflow_run(run_name=f"Pipeline_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        # 1. Ingestion (Load raw data)
        try:
            channel_raw = pd.read_csv("data/channel_data.csv")
            video_raw = pd.read_csv("data/video_data.csv")
        except FileNotFoundError:
            print("Raw data not found. Please run data/generate_data.py first.")
            return False

        # 2. Validation
        print("Validating data quality...")
        validate_data_quality(channel_raw, ['date', 'subscribers', 'total_views'])
        validate_data_quality(video_raw, ['published_at', 'views', 'likes'])

        # 3. Processing & Feature Engineering
        print("Processing and Engineering features...")
        channel_df = process_channel_data(channel_raw)
        video_df = process_video_data(video_raw)
        
        channel_features = engineer_channel_features(channel_df, video_df)
        
        # 4. Modeling, Evaluation, and Persistence (MLflow logging happens inside)
        print("Training models and evaluating performance...")
        results = forecast_channel_growth(channel_features)

        # 5. Experiment Tracking (Log summary metrics to the parent run)
        if 'metrics' in results:
            for metric_name, eval_metrics in results['metrics'].items():
                log_to_mlflow(metric_name, eval_metrics, params={"model_type": "prophet"})
            
    print(f"[{datetime.now()}] Pipeline completed successfully!")
    return True

if __name__ == "__main__":
    run_ml_pipeline()
