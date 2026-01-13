import pandas as pd
import yt_dlp
import ffmpeg
import os
import json
from openpyxl.utils import column_index_from_string

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

cfg = load_config()
d_cfg = cfg['download_config']

def process_video(url, rank):
    temp_file = os.path.join(d_cfg['temp_dir'], f"temp_{rank}.mp4")
    output_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            ydl.params['remote_components'] = ['ejs:github'] 
            info = ydl.extract_info(url, download=False)
            heatmap = info.get('heatmap')
            duration_total = info.get('duration')
            
        if heatmap:
            start = max(0, max(heatmap, key=lambda x: x['value'])['start_time'] - d_cfg['before_highlight'])
        elif duration_total:
            start = duration_total * d_cfg['chorus_percentage']
        else:
            start = d_cfg['default_start']

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': temp_file, 'quiet': True, 'remote_components': ['ejs:github']
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])

        (
            ffmpeg.input(temp_file, ss=start, t=d_cfg['clip_duration'])
            .output(output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', crf=23)
            .run(overwrite_output=True, quiet=True)
        )
        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✓ Rank {rank} scaricato.")
        return True
    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✗ Errore Rank {rank}: {e}")
        return False

if __name__ == "__main__":
    if not os.path.exists(d_cfg['output_dir']): os.makedirs(d_cfg['output_dir'])
    if not os.path.exists(d_cfg['temp_dir']): os.makedirs(d_cfg['temp_dir'])
    
    df = pd.read_excel(cfg['excel_file'])
    u_col = column_index_from_string(d_cfg['url_col']) - 1
    r_col = column_index_from_string(d_cfg['rank_col']) - 1
    
    failed = []
    for _, row in df.iterrows():
        if pd.isna(row.iloc[u_col]): continue
        if not process_video(row.iloc[u_col], row.iloc[r_col]):
            failed.append({'Rank': row.iloc[r_col], 'URL': row.iloc[u_col]})
            
    if failed: pd.DataFrame(failed).to_csv(d_cfg['failed_log'], index=False)