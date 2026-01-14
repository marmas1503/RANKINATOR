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

def calculate_highlight(heatmap, total_duration, manual_ts, total_clip_duration, d_cfg):
    """
    manual_ts: secondi estratti dall'Excel (o None)
    total_clip_duration: durata totale della clip (es. 30s)
    """
    start_point = 0

    # 1. Se c'è un timestamp manuale
    if manual_ts is not None:
        # Iniziamo 1 secondo prima del timestamp indicato
        start_point = max(0, manual_ts - 1)
    
    # 2. Se non c'è manuale, usiamo la Heatmap
    elif heatmap:
        best_point = max(heatmap, key=lambda x: x['value'])
        start_point = best_point.get('start_time', total_duration / 2)
    
    # 3. Fallback
    else:
        start_point = total_duration / 2

    # --- CONTROLLO SICUREZZA FINE VIDEO ---
    # Se il punto di inizio + la durata della clip supera la fine del video...
    if start_point + total_clip_duration > total_duration:
        # Sposta l'inizio indietro per far stare tutta la clip
        start_point = max(0, total_duration - total_clip_duration)

    return start_point