import pandas as pd
import os

def perform_weekend_analysis(channel_df: pd.DataFrame) -> dict:
    """
    Compares weekend vs weekday performance for daily views and subscriber gains.
    """
    if channel_df.empty or 'date' not in channel_df.columns:
        return {}
        
    df = channel_df.copy()
    
    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Create day of week (0=Monday, 6=Sunday)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6])
    
    # If total_views exists, we need daily views to compare
    if 'total_views' in df.columns and 'daily_views' not in df.columns:
        df['daily_views'] = df['total_views'].diff().fillna(0)
    
    metrics = {}
    if 'daily_views' in df.columns:
        weekend_views = df[df['is_weekend']]['daily_views'].mean()
        weekday_views = df[~df['is_weekend']]['daily_views'].mean()
        metrics['avg_weekend_views'] = weekend_views
        metrics['avg_weekday_views'] = weekday_views
        metrics['weekend_view_diff_pct'] = ((weekend_views - weekday_views) / weekday_views * 100) if weekday_views > 0 else 0
        
    if 'daily_subscriber_gain' in df.columns:
        weekend_subs = df[df['is_weekend']]['daily_subscriber_gain'].mean()
        weekday_subs = df[~df['is_weekend']]['daily_subscriber_gain'].mean()
        metrics['avg_weekend_subs'] = weekend_subs
        metrics['avg_weekday_subs'] = weekday_subs
        metrics['weekend_sub_diff_pct'] = ((weekend_subs - weekday_subs) / weekday_subs * 100) if weekday_subs > 0 else 0
        
    return metrics

def generate_rule_based_insights(channel_df: pd.DataFrame) -> list:
    """
    Rule-based detection for growth drops, engagement declines.
    """
    insights = []
    
    if channel_df.empty:
        return insights
        
    # Get latest data point
    latest = channel_df.iloc[-1]
    
    # Check for subscriber growth drop compared to 30-day average
    if 'daily_subscriber_gain' in channel_df.columns and 'daily_subscriber_gain_rolling_30' in channel_df.columns:
        current_gain = latest['daily_subscriber_gain']
        avg_30d_gain = latest['daily_subscriber_gain_rolling_30']
        
        if avg_30d_gain > 0 and current_gain < (avg_30d_gain * 0.8):
            insights.append(f"⚠️ Subscriber growth is dropping. Current gain ({current_gain}) is 20%+ below the 30-day average ({avg_30d_gain:.1f}).")
            
    # Add more rules as needed...
    
    if not insights:
        insights.append("✅ All key metrics are stable or growing.")
        
    return insights

import google.generativeai as genai

def generate_genai_insights(metrics_summary: dict, open_api_key: str = None) -> str:
    """
    Uses Google Gemini LLM to convert metrics into human-readable insights.
    """
    # Look for GEMINI_API_KEY instead of OPENAI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return "⚠️ GEMINI_API_KEY is not set in your .env file. You can get a free key at https://aistudio.google.com/"
        
    try:
        genai.configure(api_key=api_key)
        
        # Use gemini-flash-latest which is fast and supports free tier
        model = genai.GenerativeModel('gemini-flash-latest')
        
        prompt = f"""
        You are an expert YouTube growth strategist. Analyze the following channel performance summary and provide 3 actionable recommendations to improve growth and revenue. Keep it concise.
        
        Performance Summary:
        {metrics_summary}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating insights: {str(e)}"
