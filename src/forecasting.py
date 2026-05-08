import pandas as pd
import numpy as np
import joblib
import os
import mlflow
import mlflow.prophet
from prophet import Prophet
from sklearn.metrics import mean_absolute_error

def forecast_metric(df: pd.DataFrame, metric: str, periods: int = 30) -> tuple:
    """
    Uses Prophet to forecast a specific time series metric.
    Returns: (forecast_df, model, metrics_dict)
    """
    if 'date' not in df.columns or metric not in df.columns:
        raise ValueError(f"Dataframe must contain 'date' and '{metric}' columns.")
        
    prophet_df = df[['date', metric]].rename(columns={'date': 'ds', metric: 'y'})
    prophet_df = prophet_df.dropna()
    
    if len(prophet_df) < 10:
        return pd.DataFrame(), None, {}
        
    # Split for evaluation
    test_size = min(len(prophet_df) // 5, 30)
    train_df = prophet_df.iloc[:-test_size]
    test_df = prophet_df.iloc[-test_size:]
    
    model = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True, uncertainty_samples=0)
    model.fit(train_df)
    
    # 1. Evaluate
    future_test = model.make_future_dataframe(periods=test_size)
    forecast_test = model.predict(future_test)
    y_pred = forecast_test.tail(test_size)['yhat']
    y_true = test_df['y']
    
    mae = mean_absolute_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if (y_true != 0).all() else 0
    
    eval_metrics = {
        'mae': round(float(mae), 2),
        'mape': round(float(mape), 2),
        'accuracy': round(float(100 - mape), 2) if mape < 100 else 0.0
    }
    
    # 2. MLflow Tracking (Individual Metric Level)
    with mlflow.start_run(run_name=f"Forecast_{metric}", nested=True):
        mlflow.log_param("metric", metric)
        mlflow.log_param("forecast_periods", periods)
        mlflow.log_metrics({f"eval_{k}": v for k, v in eval_metrics.items()})
        mlflow.prophet.log_model(model, artifact_path=f"model_{metric}")
    
    # 3. Final fit on all data
    final_model = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True)
    final_model.fit(prophet_df)
    
    future = final_model.make_future_dataframe(periods=periods)
    forecast = final_model.predict(future)
    
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], final_model, eval_metrics

def save_model(model, model_name: str):
    """Saves the trained model to src/models/"""
    path = f"src/models/{model_name}.pkl"
    joblib.dump(model, path)
    return path

def load_model(model_name: str):
    """Loads a model from src/models/"""
    path = f"src/models/{model_name}.pkl"
    if os.path.exists(path):
        return joblib.load(path)
    return None

def forecast_channel_growth(channel_df: pd.DataFrame, periods: int = 30, cpm: float = 5.0) -> dict:
    """
    Enhanced forecast with evaluation and model objects.
    """
    results = {'forecasts': {}, 'metrics': {}, 'models': {}}
    
    if 'subscribers' in channel_df.columns:
        subs_forecast, subs_model, subs_metrics = forecast_metric(channel_df, 'subscribers', periods)
        if not subs_forecast.empty:
            subs_forecast['daily_subscriber_gain_pred'] = subs_forecast['yhat'].diff().fillna(0).clip(lower=0)
            results['forecasts']['subscribers'] = subs_forecast
            results['metrics']['subscribers'] = subs_metrics
            results['models']['subscribers'] = subs_model
            save_model(subs_model, "subscribers_forecast")
        
    if 'total_views' in channel_df.columns:
        views_forecast, views_model, views_metrics = forecast_metric(channel_df, 'total_views', periods)
        
        if not views_forecast.empty:
            views_forecast['daily_views_pred'] = views_forecast['yhat'].diff().fillna(0).clip(lower=0)
            views_forecast['projected_daily_revenue'] = (views_forecast['daily_views_pred'] / 1000) * cpm
            
            projected_total_revenue = views_forecast.tail(periods)['projected_daily_revenue'].sum()
            
            results['forecasts']['total_views'] = views_forecast
            results['metrics']['total_views'] = views_metrics
            results['models']['total_views'] = views_model
            results['projected_revenue'] = projected_total_revenue
            save_model(views_model, "views_forecast")
            
    return results
