import os
import pandas as pd
import time
from openpyxl.utils import column_index_from_string
import yt_dlp

# Importiamo i tuoi moduli
from modules.config_loader import load_config
from modules.utils import timestamp_to_seconds, seconds_to_hms, is_valid_video_url
from modules.audio_analyzer import get_start_audio, calculate_highlight
from modules.video_processor import download_and_process

def get_rank_settings(rank, d_cfg):
    """Recupera durate e split dal config"""
    duration_map = d_cfg.get('duration_map', {})
    default_dur = d_cfg.get('default_duration', 30)
    default_split = d_cfg.get('default_split_percentage', 0.5)
    
    for r_range, settings in duration_map.items():
        try:
            start_r, end_r = map(int, r_range.split('-'))
            if start_r <= rank <= end_r:
                if isinstance(settings, dict):
                    return settings.get('total', default_dur), settings.get('split', default_split)
                return settings, default_split
        except: continue
    return default_dur, default_split

def main():
    print("🚀 [MAIN] Avvio Rankinator...")
    cfg = load_config()
    d_cfg = cfg['download_config']
    
    # Pulizia/Creazione cartelle
    os.makedirs(d_cfg['output_dir'], exist_ok=True)
    os.makedirs(d_cfg['temp_dir'], exist_ok=True)

    print(f"📖 [MAIN] Lettura Excel: {cfg['excel_file']}")
    df = pd.read_excel(cfg['excel_file'])
    
    u_idx = column_index_from_string(d_cfg['url_col']) - 1
    r_idx = column_index_from_string(d_cfg['rank_col']) - 1
    ts_idx = column_index_from_string(d_cfg.get('timestamp_col')) - 1 if d_cfg.get('timestamp_col') else None

    for index, row in df.iterrows():
        rank = row.iloc[r_idx]
        url = str(row.iloc[u_idx]).strip()
        manual_ts = row.iloc[ts_idx] if ts_idx is not None else None

        if pd.isna(url) or url == "nan" or not is_valid_video_url(url):
            print(f"⏩ [MAIN] Salto riga {index+1}: URL non valido ({url})")
            continue

        print(f"\n--- 🛠️  ELABORAZIONE RANK {rank} ---")
        start_exec = time.time()

        try:
            # 1. Recupero Info e URL Audio
            print(f"📡 [STEP 1] Estrazione metadati da YouTube...")
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                # Fallback per l'URL audio necessario per la silence detection
                audio_url = info.get('url') or info['formats'][-1]['url']

            # 2. Analisi (Moduli Analyzer)
            print(f"🔍 [STEP 2] Analisi audio e heatmap...")
            start_intro = get_start_audio(audio_url, d_cfg)
            start_highlight = calculate_highlight(info.get('heatmap'), info.get('duration', 0), timestamp_to_seconds(manual_ts), d_cfg)

            # 3. Calcolo durate specifiche per questo Rank
            total_dur, split_pct = get_rank_settings(rank, d_cfg)
            dur_a = total_dur * split_pct
            dur_b = total_dur * (1 - split_pct)
            
            temp_file = os.path.join(d_cfg['temp_dir'], f"temp_{rank}.mp4")
            output_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")

            # 4. Processamento Video (Modulo Video Processor)
            print(f"🎬 [STEP 3] Passaggio al Video Processor...")
            download_and_process(
                url, rank, start_intro, start_highlight, 
                total_dur, dur_a, dur_b, d_cfg, 
                temp_file, output_path
            )

            print(f"✅ [MAIN] Rank {rank} completato in {time.time() - start_exec:.1f}s")

        except Exception as e:
            print(f"❌ [MAIN] ERRORE CRITICO al Rank {rank}: {str(e)}")
            import traceback
            traceback.print_exc() # Questo ti dice esattamente IN QUALE RIGA è l'errore

if __name__ == "__main__":
    main()