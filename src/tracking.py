import mlflow
import os

# Set up local tracking URI
mlflow.set_tracking_uri("file:./mlruns")
mlflow.set_experiment("TubePulse_YouTube_Intelligence")

def start_mlflow_run(run_name: str):
    """Starts a new MLflow run."""
    return mlflow.start_run(run_name=run_name)

def log_to_mlflow(metric_name: str, eval_metrics: dict, params: dict = None):
    """
    Logs metrics and parameters to MLflow.
    """
    if params:
        mlflow.log_params(params)
    
    # Prefix metrics with the metric name (e.g., subscribers_mae)
    prefixed_metrics = {f"{metric_name}_{k}": v for k, v in eval_metrics.items()}
    mlflow.log_metrics(prefixed_metrics)
    
    print(f"Logged to MLflow: {metric_name} Accuracy: {eval_metrics.get('accuracy')}%")

def get_latest_metrics(metric_name: str):
    """
    Retrieves the latest metrics from MLflow for a specific metric.
    Note: In a real app, we'd query the MLflow client. 
    For now, we return the local metrics if available.
    """
    # This is a simplified version. Usually, you'd use mlflow.search_runs()
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("TubePulse_YouTube_Intelligence")
    if experiment:
        runs = client.search_runs(experiment.experiment_id, order_by=["attribute.start_time DESC"], max_results=1)
        if runs:
            latest_run = runs[0]
            # Find the accuracy metric for the specific metric_name
            acc_key = f"{metric_name}_accuracy"
            if acc_key in latest_run.data.metrics:
                return {
                    "accuracy": latest_run.data.metrics.get(acc_key),
                    "mae": latest_run.data.metrics.get(f"{metric_name}_mae"),
                    "mape": latest_run.data.metrics.get(f"{metric_name}_mape")
                }
    return None
