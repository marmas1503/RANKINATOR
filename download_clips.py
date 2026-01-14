import os
import pandas as pd
import time
from multiprocessing import Pool
from openpyxl.utils import column_index_from_string
import yt_dlp
from tqdm import tqdm

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
        
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get('url') or info['formats'][-1]['url']

        start_intro = get_start_audio(audio_url, d_cfg)
        start_highlight = calculate_highlight(info.get('heatmap'), info.get('duration', 0), 
                                              timestamp_to_seconds(manual_ts), d_cfg)

        total_dur, split_pct = get_rank_settings(rank, d_cfg)
        dur_a, dur_b = total_dur * split_pct, total_dur * (1 - split_pct)

        download_and_process(url, rank, start_intro, start_highlight, total_dur, 
                             dur_a, dur_b, d_cfg, temp_file, output_path)
        return {'Rank': rank, 'Status': 'OK', 'Timestamp': seconds_to_hms(start_highlight)}
    except Exception as e:
        return {'Rank': rank, 'Status': f'Error: {str(e)}', 'Timestamp': 'FAILED'}

def main():
    cfg = load_config()
    g_cfg = cfg['global_settings']
    m_cfg = cfg['excel_mapping']
    d_cfg = cfg['download_config']
    
    max_workers = g_cfg.get('max_workers', 4)
    print(f"🚀 [DOWNLOADER] Avvio con {max_workers} processi simultanei.")
    
    os.makedirs(d_cfg['output_dir'], exist_ok=True)
    os.makedirs(d_cfg['temp_dir'], exist_ok=True)

    df = pd.read_excel(g_cfg['excel_file'])
    u_idx = column_index_from_string(m_cfg['url_col']) - 1
    r_idx = column_index_from_string(m_cfg['rank_col']) - 1
    ts_idx = column_index_from_string(m_cfg['timestamp_col']) - 1

    tasks = [(int(row.iloc[r_idx]), str(row.iloc[u_idx]).strip(), row.iloc[ts_idx], d_cfg) 
             for _, row in df.iterrows() if is_valid_video_url(str(row.iloc[u_idx]))]

    results = []
    with Pool(processes=max_workers) as pool:
        for result in tqdm(pool.imap_unordered(worker, tasks), total=len(tasks), desc="Downloading Clips"):
            results.append(result)

    pd.DataFrame(results).sort_values('Rank').to_csv('report_download.csv', index=False)
    print("✨ Download completato.")

if __name__ == "__main__":
    main()