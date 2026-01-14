import pandas as pd
import re
import datetime

def timestamp_to_seconds(ts):
    # 1. Gestione se è già un oggetto tempo di Python/Excel
    if isinstance(ts, (datetime.time, datetime.datetime)):
        return ts.hour * 3600 + ts.minute * 60 + ts.second
    
    # 2. Pulizia stringa
    ts_str = str(ts).strip().lower()
    if ts_str in ['nan', '', 'none', '0', '00:00']:
        return None
    
    try:
        # 3. Gestione formati stringa (HH:MM:SS o MM:SS)
        parts = ts_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(float(ts_str))
    except:
        return None

def seconds_to_hms(seconds):
    if seconds is None: return "FAILED"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def is_valid_video_url(url):
    if not isinstance(url, str): return False
    invalid = [r'images\?q=tbn', r'\.jpg$', r'\.png$', r'\.webp$', r'gstatic\.com']
    return not any(re.search(p, url) for p in invalid)