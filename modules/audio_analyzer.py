import subprocess
import re

def get_start_audio(audio_url, d_cfg):
    try:
        threshold = d_cfg.get('silence_threshold', '-45dB')
        duration = d_cfg.get('silence_duration', '0.1')
        cmd = [
            'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1',
            '-i', audio_url, '-t', '15', '-vn', '-af', 
            f'silencedetect=n={threshold}:d={duration}', '-f', 'null', '-'
        ]
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        _, err = process.communicate()
        matches = re.findall(r'silence_end: ([\d\.]+)', err)
        silence_end = float(matches[-1]) if matches else 0.0
        if silence_end > 0:
            print(f"✂️  LOG SILENZIO: Tagliati {silence_end:.2f}s iniziali.")
        return silence_end
    except: return 0.0

def calculate_highlight(heatmap, duration_total, manual_seconds, d_cfg):
    h_limit = d_cfg.get('heatmap_limit', 0.85)
    b_highlight = d_cfg.get('before_highlight_offset', 2.0)
    
    if manual_seconds is not None:
        return max(0, manual_seconds - b_highlight)
    
    if heatmap:
        end_threshold = duration_total * h_limit
        filtered = [p for p in heatmap if p['start_time'] < end_threshold]
        if filtered:
            best = max(filtered, key=lambda x: x['value'])['start_time']
            return max(0, best - b_highlight)
            
    return duration_total * d_cfg.get('chorus_percentage', 0.25)