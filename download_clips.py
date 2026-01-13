import pandas as pd
import yt_dlp
import ffmpeg
import os
import json
import re
import subprocess
from openpyxl.utils import column_index_from_string

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def timestamp_to_seconds(ts):
    if pd.isna(ts) or str(ts).strip() == "":
        return None
    try:
        parts = str(ts).strip().split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return float(ts)
    except:
        return None

# Funzione utile per convertire i secondi di nuovo in formato leggibile 00:00 per il report
def seconds_to_hms(seconds):
    if seconds is None: return "FAILED"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def get_rank_settings(rank, d_cfg):
    duration_map = d_cfg.get('duration_map', {})
    default_dur = d_cfg.get('default_duration', 15)
    default_split = d_cfg.get('default_split_percentage', 0.5)
    for r_range, settings in duration_map.items():
        try:
            start_r, end_r = map(int, r_range.split('-'))
            if start_r <= rank <= end_r:
                if isinstance(settings, dict):
                    return settings.get('total', default_dur), settings.get('split', default_split)
                else:
                    return settings, default_split
        except: continue
    return default_dur, default_split

def get_start_audio(audio_url, d_cfg):
    try:
        threshold = str(d_cfg.get('silence_threshold', '-45dB'))
        duration = str(d_cfg.get('silence_duration', '0.1'))
        cmd = [
            'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
            '-i', audio_url, '-t', '15', '-vn', '-sn',
            '-af', f'silencedetect=n={threshold}:d={duration}',
            '-f', 'null', '-'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _, err = process.communicate()
        matches = re.findall(r'silence_end: ([\d\.]+)', err)
        return float(matches[-1]) if matches else 0.0
    except:
        return 0.0

def process_video(url, rank, manual_ts=None):
    cfg = load_config()
    d_cfg = cfg['download_config']
    output_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")
    temp_file = os.path.join(d_cfg['temp_dir'], f"temp_{rank}.mp4")
    
    total_dur, split_pct = get_rank_settings(rank, d_cfg)
    dur_a, dur_b = total_dur * split_pct, total_dur * (1 - split_pct)
    xfade = d_cfg.get('crossfade_duration', 1.0)
    fmt_h264_aac = 'bestvideo[ext=mp4][vcodec^=avc1][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    start_highlight = 0.0 # Valore di fallback

    try:
        # 1. Estrazione Info
        with yt_dlp.YoutubeDL({'quiet': True, 'format': 'bestaudio[ext=m4a]/bestaudio'}) as ydl:
            audio_info = ydl.extract_info(url, download=False)
            audio_url = audio_info['url']

        with yt_dlp.YoutubeDL({'quiet': True, 'format': fmt_h264_aac}) as ydl:
            info = ydl.extract_info(url, download=False)
            heatmap = info.get('heatmap')
            duration_total = info.get('duration', 0)

        start_intro = get_start_audio(audio_url, d_cfg)
        
        # 4. Calcolo highlight (Spostato prima del controllo video corto per il report)
        manual_seconds = timestamp_to_seconds(manual_ts)
        if manual_seconds is not None:
            start_highlight = max(0, manual_seconds - 2)
        elif heatmap:
            best_moment = max(heatmap, key=lambda x: x['value'])['start_time']
            start_highlight = max(0, best_moment - 2)
        else:
            start_highlight = duration_total * d_cfg.get('chorus_percentage', 0.25)

        if (start_highlight + dur_b) > duration_total:
            start_highlight = max(0, duration_total - dur_b - 0.5)

        # 3. Controllo Video Corto
        if duration_total <= total_dur:
            ydl_opts_full = {
                'format': fmt_h264_aac, 'outtmpl': output_path, 'quiet': True,
                'external_downloader': 'ffmpeg',
                'external_downloader_args': {
                    'ffmpeg_i': ['-ss', str(start_intro)],
                    'ffmpeg_o': ['-vcodec', 'libx264', '-acodec', 'aac', '-pix_fmt', 'yuv420p']
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts_full) as ydl: ydl.download([url])
            return start_highlight

        # 5. Esecuzione Tagli
        if (start_intro + dur_a >= start_highlight):
            ydl_opts_direct = {
                'format': fmt_h264_aac, 'outtmpl': output_path, 'quiet': True,
                'external_downloader': 'ffmpeg',
                'external_downloader_args': {
                    'ffmpeg_i': ['-ss', str(start_intro), '-t', str(total_dur)],
                    'ffmpeg_o': ['-vcodec', 'libx264', '-acodec', 'aac', '-pix_fmt', 'yuv420p']
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts_direct) as ydl: ydl.download([url])
        else:
            ydl_opts_temp = {'format': fmt_h264_aac, 'outtmpl': temp_file, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts_temp) as ydl: ydl.download([url])

            seg_a = ffmpeg.input(temp_file, ss=start_intro, t=dur_a)
            seg_b = ffmpeg.input(temp_file, ss=start_highlight, t=dur_b)
            v_merged = ffmpeg.filter([seg_a.video, seg_b.video], 'xfade', transition='fade', duration=xfade, offset=dur_a-xfade)
            a_merged = ffmpeg.filter([seg_a.audio, seg_b.audio], 'acrossfade', d=xfade)
            
            ffmpeg.output(v_merged, a_merged, output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', crf=21).run(overwrite_output=True, quiet=True)

        if os.path.exists(temp_file): os.remove(temp_file)
        return start_highlight
    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✗ Errore Rank {rank}: {e}")
        return None

if __name__ == "__main__":
    cfg = load_config()
    d_cfg = cfg['download_config']
    os.makedirs(d_cfg['output_dir'], exist_ok=True)
    os.makedirs(d_cfg['temp_dir'], exist_ok=True)
    
    df = pd.read_excel(cfg['excel_file'])
    u_col_idx = column_index_from_string(d_cfg['url_col']) - 1
    r_col_idx = column_index_from_string(d_cfg['rank_col']) - 1
    ts_col_name = d_cfg.get('timestamp_col')
    ts_col_idx = column_index_from_string(ts_col_name) - 1 if ts_col_name else None
    
    # Lista per accumulare i dati del report
    report_data = []

    for _, row in df.iterrows():
        url = row.iloc[u_col_idx]
        rank = row.iloc[r_col_idx]
        ts_val = row.iloc[ts_col_idx] if ts_col_idx is not None else None
        
        if pd.isna(url) or pd.isna(rank): continue
        
        # Esecuzione e recupero timestamp
        result_ts = process_video(url, int(rank), ts_val)
        
        # Aggiunta al report
        report_data.append({
            'Rank': int(rank),
            'Link': url,
            'Highlight_Timestamp': seconds_to_hms(result_ts)
        })

    # Generazione CSV
    report_df = pd.DataFrame(report_data)
    report_df.to_csv('report.csv', index=False, encoding='utf-8')
    print("\n📄 report.csv generato con successo.")