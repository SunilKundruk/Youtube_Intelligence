import pandas as pd
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_data_quality(df: pd.DataFrame, expected_cols: list) -> bool:
    """
    Validates data quality based on expected columns, null rates, and logic.
    Returns True if valid, raises ValueError if critical issues are found.
    """
    if df.empty:
        raise ValueError("Dataframe is empty.")

    # 1. Check for missing columns
    missing_cols = [col for col in expected_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"Missing columns detected: {missing_cols}")
        # Not always critical if we have fallback logic, but good to know
    
    # 2. Check for excessive Nulls (e.g. > 50%)
    null_counts = df.isnull().mean()
    high_null_cols = null_counts[null_counts > 0.5].index.tolist()
    if high_null_cols:
        logger.warning(f"High null rate (>50%) in columns: {high_null_cols}")
        
    # 3. Check for negative growth in cumulative columns if applicable
    # (This logic is already handled in cleaning, but we can report anomalies here)
    
    # 4. Check for date continuity
    if 'date' in df.columns:
        df_sorted = df.sort_values('date')
        date_diffs = df_sorted['date'].diff().dt.days
        if (date_diffs > 1).any():
            logger.info("Gaps detected in date sequence.")
            
    return True

def process_channel_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and processes Channel Data.
    Expected Columns: Date, channel_id, channel_title, subscribers, total_views, video_count, Revenue
    """
    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # 1. Standardize column names to lowercase
    df.columns = [col.strip().lower() for col in df.columns]
    
    # Column mapping for common variations (FORCE priority for 'total' names)
    synonyms = {
        'subscribers': ['total subscribers', 'subscriber count', 'subscribers'],
        'total_views': ['total views', 'view count', 'total_views']
    }
    
    for standard, variations in synonyms.items():
        # Look for the best match (e.g. 'total subscribers' is better than 'subscribers')
        best_match = None
        for var in variations:
            if var in df.columns:
                best_match = var
        
        if best_match:
            # If we found a better name, or if the current one isn't the standard one, rename it
            if best_match != standard:
                # If 'subscribers' already exists but we found 'total subscribers', overwrite 'subscribers'
                df[standard] = df[best_match]
    
    # Ensure revenue is handled
    if 'revenue' not in df.columns:
        for rev_var in ['earnings', 'estimated revenue', 'income']:
            if rev_var in df.columns:
                df['revenue'] = df[rev_var]
                break
    
    # 2. Convert Date to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # 3. Sort by date
    df = df.sort_values(by='date').reset_index(drop=True)
    
    # 4. Handle missing values and detect cumulative vs daily
    numeric_cols = ['subscribers', 'total_views', 'video_count', 'revenue']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Auto-detection: If values are small or if the data DECREASES at any point,
            # it's likely daily gains rather than a lifetime total.
            if col in ['subscribers', 'total_views']:
                # Logic: If it ever drops, or if the start is near zero relative to max
                has_drops = (df[col].diff().dropna() < 0).any()
                is_small  = (df[col].max() < 1000)
                starts_low = (df[col].iloc[0] < df[col].max() * 0.1) if df[col].max() > 0 else False
                
                if (has_drops or is_small or starts_low) and df[col].mean() > 0:
                    df[col] = df[col].cumsum()
                
            if col == 'revenue':
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].ffill().bfill()
                
    return df

def process_video_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and processes Video Data.
    Expected Columns: Date, video_id, channel_id, title, published_at, views, likes, comments, duration_seconds
    """
    df = df.copy()
    
    # 1. Standardize column names
    df.columns = [col.strip().lower() for col in df.columns]
    
    # 2. Convert Dates to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'])
        
    # 3. Handle missing values
    numeric_cols = ['views', 'likes', 'comments', 'duration_seconds']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Fill missing engagement metrics with 0
            df[col] = df[col].fillna(0)
            
    # For text columns
    if 'title' in df.columns:
        df['title'] = df['title'].fillna("Unknown")
        
    return df
