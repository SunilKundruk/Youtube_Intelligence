import pandas as pd
import numpy as np
from datetime import timedelta, date

# Constants
START_DATE = date(2025, 1, 1)
DAYS = 180 # 6 months of data
CHANNEL_ID = "UC_synth_channel_123"
CHANNEL_TITLE = "Tech Mastery AI"

def generate_synthetic_data():
    dates = [START_DATE + timedelta(days=i) for i in range(DAYS)]
    
    # 1. Generate Channel Data
    # Start with 10k subs, grow daily, with some noise
    daily_sub_gains = np.random.normal(loc=50, scale=15, size=DAYS).astype(int)
    # Weekends get a boost
    for i, d in enumerate(dates):
        if d.weekday() >= 5: # 5=Sat, 6=Sun
            daily_sub_gains[i] += int(np.random.normal(loc=30, scale=10))
            
    subscribers = np.cumsum(daily_sub_gains) + 10000
    
    # Views: correlated with subs, more on weekends
    daily_views = subscribers * np.random.normal(loc=0.05, scale=0.01, size=DAYS)
    for i, d in enumerate(dates):
        if d.weekday() >= 5:
            daily_views[i] *= 1.3 # 30% boost on weekends
    total_views = np.cumsum(daily_views).astype(int)
    
    # Revenue: approx $5 CPM
    daily_revenue = (daily_views / 1000) * 5.0 * np.random.normal(loc=1.0, scale=0.1, size=DAYS)
    
    # Video Count
    video_count = np.linspace(100, 150, DAYS).astype(int)
    
    channel_df = pd.DataFrame({
        'Date': dates,
        'channel_id': CHANNEL_ID,
        'channel_title': CHANNEL_TITLE,
        'subscribers': subscribers,
        'total_views': total_views,
        'video_count': video_count,
        'Revenue': np.round(daily_revenue, 2)
    })
    
    # 2. Generate Video Data
    # Let's say they publish 2 videos a week (approx 50 videos in 180 days)
    num_videos = 50
    publish_dates = np.random.choice(dates, size=num_videos, replace=False)
    publish_dates.sort()
    
    video_ids = [f"vid_{i:04d}" for i in range(num_videos)]
    titles = [f"Mastering Python Part {i+1}" for i in range(num_videos)]
    
    video_views = np.random.lognormal(mean=10.0, sigma=1.0, size=num_videos).astype(int)
    likes = (video_views * np.random.uniform(0.02, 0.08, size=num_videos)).astype(int)
    comments = (likes * np.random.uniform(0.05, 0.15, size=num_videos)).astype(int)
    duration = np.random.randint(300, 1200, size=num_videos) # 5 to 20 mins
    
    # Duplicate some rows to show daily performance of videos (simplified here by just showing one row per video published_at)
    video_df = pd.DataFrame({
        'Date': publish_dates, # Let's assume snapshot on publish date or similar
        'video_id': video_ids,
        'channel_id': CHANNEL_ID,
        'title': titles,
        'published_at': publish_dates,
        'views': video_views,
        'likes': likes,
        'comments': comments,
        'duration_seconds': duration
    })
    
    # Save to CSV
    channel_df.to_csv('c:/Users/sunil/OneDrive/Desktop/YOUTUBE/data/channel_data.csv', index=False)
    video_df.to_csv('c:/Users/sunil/OneDrive/Desktop/YOUTUBE/data/video_data.csv', index=False)
    
    print("Synthetic data generated successfully in data/ folder!")

if __name__ == "__main__":
    generate_synthetic_data()
