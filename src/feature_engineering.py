import pandas as pd
import numpy as np

def engineer_channel_features(channel_df: pd.DataFrame, video_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Creates features like daily_subscriber_gain, uploads_per_day, and rolling averages.
    """
    df = channel_df.copy()
    
    # Ensure sorted by date
    if 'date' in df.columns:
        df = df.sort_values(by='date').reset_index(drop=True)
    
    # 1. Daily subscriber gain and daily views
    if 'subscribers' in df.columns:
        df['daily_subscriber_gain'] = df['subscribers'].diff().fillna(0)
    if 'total_views' in df.columns:
        df['daily_views'] = df['total_views'].diff().fillna(0)
        
    # 2. Rolling Averages (7, 30 days) for key metrics
    # We assume 'date' has daily frequency. For more accuracy, could set 'date' as index.
    metrics = ['subscribers', 'total_views', 'revenue', 'daily_subscriber_gain']
    for metric in metrics:
        if metric in df.columns:
            df[f'{metric}_rolling_7'] = df[metric].rolling(window=7, min_periods=1).mean()
            df[f'{metric}_rolling_30'] = df[metric].rolling(window=30, min_periods=1).mean()
            
    # 3. Uploads per day (if video_df is provided)
    if video_df is not None and 'published_at' in video_df.columns:
        # Extract date from published_at
        video_df_copy = video_df.copy()
        video_df_copy['publish_date'] = video_df_copy['published_at'].dt.date
        uploads_per_day = video_df_copy.groupby('publish_date').size().reset_index(name='uploads_per_day')
        uploads_per_day['publish_date'] = pd.to_datetime(uploads_per_day['publish_date'])
        
        # Merge with channel df
        df = pd.merge(df, uploads_per_day, left_on='date', right_on='publish_date', how='left')
        df['uploads_per_day'] = df['uploads_per_day'].fillna(0)
        df.drop(columns=['publish_date'], inplace=True)
        
    return df

def engineer_video_features(video_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates features like engagement_rate.
    """
    df = video_df.copy()
    
    # 1. Engagement Rate: (Likes + Comments) / Views
    if all(col in df.columns for col in ['likes', 'comments', 'views']):
        # Avoid division by zero
        df['engagement_rate'] = np.where(
            df['views'] > 0, 
            (df['likes'] + df['comments']) / df['views'], 
            0
        )
        
    return df
