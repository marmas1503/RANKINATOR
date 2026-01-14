import pandas as pd
import re

def timestamp_to_seconds(ts):
    if pd.isna(ts) or str(ts).strip() == "": return None
    try:
        parts = str(ts).strip().split(':')
        if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
        return float(ts)
    except: return None

def seconds_to_hms(seconds):
    if seconds is None: return "FAILED"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def is_valid_video_url(url):
    if not isinstance(url, str): return False
    invalid = [r'images\?q=tbn', r'\.jpg$', r'\.png$', r'\.webp$', r'gstatic\.com']
    return not any(re.search(p, url) for p in invalid)