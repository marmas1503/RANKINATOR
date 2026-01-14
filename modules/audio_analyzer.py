import subprocess
import re
import os
import subprocess
import re

import subprocess
import re
import os

import subprocess
import re
import os

def get_audio_stats(audio_url):
    """Analizza il volume massimo dei primi 5 secondi per debug."""
    command = [
        'ffmpeg', '-hide_banner',
        '-t', '5', '-i', audio_url,
        '-map', '0:a',
        '-af', 'volumedetect',
        '-f', 'null', 'NUL' if os.name == 'nt' else '/dev/null'
    ]
    try:
        process = subprocess.Popen(command, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        _, stderr = process.communicate()
        max_vol_match = re.search(r"max_volume: ([\-\d\.]+) dB", stderr)
        if max_vol_match:
            return float(max_vol_match.group(1))
    except:
        pass
    return None

def get_start_audio(audio_url, d_cfg):
    threshold = float(d_cfg.get('silence_threshold', -40))
    duration = float(d_cfg.get('silence_duration', 0.5))
    
    # Debug del volume reale
    max_v = get_audio_stats(audio_url)
    if max_v is not None:
        print(f"📊 [DEBUG AUDIO] Picco Max: {max_v}dB (Soglia impostata: {threshold}dB)")
        if max_v > threshold:
            print(f"⚠️  Il rumore di fondo ({max_v}dB) è più forte della soglia. Il silenzio NON verrà rilevato.")
    
    # Comando principale per il rilevamento silenzio
    command = [
        'ffmpeg', '-hide_banner',
        '-t', '60', 
        '-i', audio_url,
        '-map', '0:a', # Forza l'analisi solo sulla traccia audio
        '-af', f'aresample=async=1,silencedetect=n={threshold}dB:d={duration}',
        '-f', 'null', 
        'NUL' if os.name == 'nt' else '/dev/null'
    ]
    
    try:
        process = subprocess.Popen(command, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        _, stderr = process.communicate()
        
        # Cerchiamo l'ultimo momento di silenzio rilevato
        silence_ends = re.findall(r"silence_end: ([\d\.]+)", stderr)
        
        if silence_ends:
            first_sound = float(silence_ends[-1])
            print(f"✅ [DEBUG AUDIO] Silenzio finito a: {first_sound}s")
            return first_sound
        
        return 0
            
    except Exception as e:
        print(f"❌ [DEBUG AUDIO] Errore FFmpeg: {e}")
        return 0

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
