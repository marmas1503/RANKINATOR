import os
import pandas as pd
import time
from multiprocessing import Pool
from openpyxl.utils import column_index_from_string
import yt_dlp
from tqdm import tqdm
import sys

from modules.config_loader import load_config
from modules.utils import timestamp_to_seconds, seconds_to_hms, is_valid_video_url
from modules.audio_analyzer import get_start_audio, calculate_highlight
from modules.video_processor import download_and_process

def get_rank_settings(rank, d_cfg):
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

def worker(task_data):
    rank, url, manual_ts, d_cfg = task_data
    try:
        temp_file = os.path.join(d_cfg['temp_dir'], f"temp_{rank}.mp4")
        output_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")
        
        # 1. Estrazione info
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get('url') or info['formats'][-1]['url']
            total_video_duration = info.get('duration', 0)

        total_dur, split_pct = get_rank_settings(rank, d_cfg)
        manual_seconds = timestamp_to_seconds(manual_ts)

        # 2. Logica di instradamento e Log dedicati
        if manual_seconds is not None:
            # --- MODALITÀ MANUALE ---
            start_intro = 0
            start_highlight = calculate_highlight(
                None, 
                total_video_duration, 
                manual_seconds, 
                total_dur, 
                d_cfg
            )
            
            # Log specifico per il manuale
            log_msg = f"📍 [Rank {rank}] Manual TS: {manual_ts}s | Start: {seconds_to_hms(start_highlight)}"
            if start_highlight < (manual_seconds - 1) and manual_seconds > 1:
                log_msg += " (⚠️ Fine video vicina, inizio anticipato)"
            print(f"\n{log_msg}")

        else:
            # --- MODALITÀ AUTOMATICA ---
            start_intro = get_start_audio(audio_url, d_cfg)
            start_highlight = calculate_highlight(
                info.get('heatmap'), 
                total_video_duration, 
                None, 
                total_dur, 
                d_cfg
            )
            print(f"\n🤖 [Rank {rank}] Auto-Highlight -> Start: {seconds_to_hms(start_highlight)} (Intro skip: {start_intro}s)")

        # 3. Esecuzione download e taglio
        download_and_process(url, rank, start_intro, start_highlight, total_dur, 
                             dur_a := total_dur * split_pct, 
                             dur_b := total_dur * (1 - split_pct), 
                             d_cfg, temp_file, output_path)
        
        return {'Rank': rank, 'Status': 'OK', 'Timestamp': seconds_to_hms(start_highlight)}

    except Exception as e:
        print(f"\n❌ [Rank {rank}] ERRORE: {str(e)}")
        return {'Rank': rank, 'Status': f'Error: {str(e)}', 'Timestamp': 'FAILED'}

def main():
    cfg = load_config()
    g_cfg, m_cfg, d_cfg = cfg['global_settings'], cfg['excel_mapping'], cfg['download_config']
    
    max_workers = g_cfg.get('max_workers', 4)
    print(f"🚀 [DOWNLOADER] Avvio {max_workers} worker paralleli.")
    
    os.makedirs(d_cfg['output_dir'], exist_ok=True)
    os.makedirs(d_cfg['temp_dir'], exist_ok=True)

    try:
        df = pd.read_excel(g_cfg['excel_file'])
        u_idx = column_index_from_string(m_cfg['url_col']) - 1
        r_idx = column_index_from_string(m_cfg['rank_col']) - 1
        ts_idx = column_index_from_string(m_cfg['timestamp_col']) - 1

        tasks = []
        for _, row in df.iterrows():
            url = str(row.iloc[u_idx]).strip()
            if is_valid_video_url(url):
                tasks.append((
                    int(row.iloc[r_idx]), 
                    url, 
                    row.iloc[ts_idx], 
                    d_cfg
                ))

        results = []
        pool = Pool(processes=max_workers)
        pbar = tqdm(total=len(tasks), desc="Progresso Totale")
        
        try:
            for result in pool.imap_unordered(worker, tasks):
                results.append(result)
                pbar.update(1)
            pool.close()
        except KeyboardInterrupt:
            print("\n🛑 Interruzione manuale! Uccisione processi...")
            pool.terminate()
            pool.join()
            os._exit(1)

        pool.join()
        pbar.close()
        
        # Report finale ordinato per Rank
        report_df = pd.DataFrame(results).sort_values('Rank')
        # Ensure top-level output folder exists and save report there
        reports_dir = os.path.dirname(d_cfg.get('output_dir', 'output/clips')) or 'output'
        os.makedirs(reports_dir, exist_ok=True)
        out_report = os.path.join(reports_dir, 'download_report.csv')
        report_df.to_csv(out_report, index=False)
        print(f"\n✨ Download completato. Report salvato: {out_report}")

    except Exception as e:
        print(f"❌ Errore critico nel Main: {e}")

if __name__ == "__main__":
    main()