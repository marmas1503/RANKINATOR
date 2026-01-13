import pandas as pd
import yt_dlp
import ffmpeg
import os
from openpyxl.utils import column_index_from_string
import config

c = config.DOWNLOAD_CONFIG

def setup_dirs():
    for d in [c['output_dir'], c['temp_dir']]:
        if not os.path.exists(d): os.makedirs(d)

def process_video(url, rank):
    temp_file = os.path.join(c['temp_dir'], f"temp_{rank}.mp4")
    output_path = os.path.join(c['output_dir'], f"{rank}_clip.mp4")

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            ydl.params['remote_components'] = ['ejs:github'] 
            info = ydl.extract_info(url, download=False)
            heatmap = info.get('heatmap')
            duration_total = info.get('duration')
            
        if heatmap:
            start = max(0, max(heatmap, key=lambda x: x['value'])['start_time'] - c['before_highlight'])
        elif duration_total:
            start = duration_total * c['chorus_percentage']
        else:
            start = c['default_start']

        ydl_dl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': temp_file, 'quiet': True, 'remote_components': ['ejs:github']
        }
        with yt_dlp.YoutubeDL(ydl_dl_opts) as ydl: ydl.download([url])

        (
            ffmpeg.input(temp_file, ss=start, t=c['clip_duration'])
            .output(output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', crf=23)
            .run(overwrite_output=True, quiet=True)
        )
        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✓ Rank {rank} completato.")
        return True
    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✗ Errore Rank {rank}: {e}")
        return False

def main():
    setup_dirs()
    df = pd.read_excel(config.EXCEL_FILE)
    u_idx = column_index_from_string(c['url_col']) - 1
    r_idx = column_index_from_string(c['rank_col']) - 1
    failed = []

    for _, row in df.iterrows():
        url, rank = row.iloc[u_idx], row.iloc[r_idx]
        if pd.isna(url): continue
        if not process_video(url, rank): failed.append({'Position': rank, 'URL': url})

    if failed: pd.DataFrame(failed).to_csv(c['failed_log'], index=False)

if __name__ == "__main__":
    main()