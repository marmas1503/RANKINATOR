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
    """Esegue SOLTANTO l'analisi del silenzio tramite FFmpeg."""
    try:
        threshold = str(d_cfg.get('silence_threshold', '-45dB'))
        duration = str(d_cfg.get('silence_duration', '0.1'))

        # Comando shell diretto per massima compatibilità
        cmd = [
            'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
            '-i', audio_url, '-t', '15', '-vn', '-sn',
            '-af', f'silencedetect=n={threshold}:d={duration}',
            '-f', 'null', '-'
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _, err = process.communicate()
        
        matches = re.findall(r'silence_end: ([\d\.]+)', err)
        if matches:
            return float(matches[-1])
        return 0.0
    except Exception as e:
        print(f"⚠️ Errore tecnico FFmpeg: {e}")
        return 0.0

def process_video(url, rank):
    cfg = load_config()
    d_cfg = cfg['download_config']
    output_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")
    temp_file = os.path.join(d_cfg['temp_dir'], f"temp_{rank}.mp4")
    
    total_dur, split_pct = get_rank_settings(rank, d_cfg)
    dur_a, dur_b = total_dur * split_pct, total_dur * (1 - split_pct)
    xfade = d_cfg.get('crossfade_duration', 1.0)

    try:
        # 1. Estrazione Info
        with yt_dlp.YoutubeDL({'quiet': True, 'format': 'bestaudio/best'}) as ydl:
            audio_info = ydl.extract_info(url, download=False)
            audio_url = audio_info['url']

        with yt_dlp.YoutubeDL({'quiet': True, 'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best'}) as ydl:
            info = ydl.extract_info(url, download=False)
            heatmap = info.get('heatmap')
            duration_total = info.get('duration', 0)
            video_url = info.get('url') or info.get('formats', [{}])[-1].get('url')

        # 2. Analisi silenzio
        print(f"🔍 Rank {rank}: Analisi silenzio...")
        start_intro = get_start_audio(audio_url, d_cfg)
        
        if start_intro > 0:
            print(f"🔇 Rank {rank}: Rilevati {start_intro:.2f}s di silenzio iniziale.")
        
        # --- CONTROLLO VIDEO TROPPO CORTO ---
        if duration_total <= total_dur:
            print(f"ℹ️ Rank {rank}: Video totale ({duration_total}s) più corto o uguale alla durata target ({total_dur}s). Scarico intero.")
            ydl_opts_full = {
                'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': output_path, 'quiet': True,
                'external_downloader': 'ffmpeg',
                'external_downloader_args': {'ffmpeg_i': ['-ss', str(start_intro)]} # Taglia solo il silenzio se c'è
            }
            with yt_dlp.YoutubeDL(ydl_opts_full) as ydl: ydl.download([url])
            return True

        # 3. Calcolo highlight con protezione fine video
        if heatmap:
            best_moment = max(heatmap, key=lambda x: x['value'])['start_time']
            start_highlight = max(0, best_moment - 2)
        else:
            start_highlight = duration_total * d_cfg.get('chorus_percentage', 0.25)

        # --- PROTEZIONE FINE VIDEO ---
        if (start_highlight + dur_b) > duration_total:
            nuovo_start = max(0, duration_total - dur_b - 0.5)
            print(f"⚠️ Rank {rank}: Highlight spostato a {nuovo_start:.1f}s (troppo vicino alla fine).")
            start_highlight = nuovo_start

        # 4. Esecuzione Tagli
        # Caso A: Clip unica (se l'intro e l'highlight si sovrappongono)
        if (start_intro + dur_a >= start_highlight):
            print(f"⚠ Rank {rank}: Clip continua senza crossfade...")
            ydl_opts_direct = {
                'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': output_path, 'quiet': True,
                'external_downloader': 'ffmpeg',
                'external_downloader_args': {'ffmpeg_i': ['-ss', str(start_intro), '-t', str(total_dur)]}
            }
            with yt_dlp.YoutubeDL(ydl_opts_direct) as ydl: ydl.download([url])
        
        # Caso B: Crossfade
        else:
            print(f"🎬 Rank {rank}: Generazione Crossfade ({dur_a:.1f}s + {dur_b:.1f}s)...")
            ydl_opts_temp = {'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]', 'outtmpl': temp_file, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts_temp) as ydl: ydl.download([url])

            seg_a = ffmpeg.input(temp_file, ss=start_intro, t=dur_a)
            seg_b = ffmpeg.input(temp_file, ss=start_highlight, t=dur_b)
            
            v_merged = ffmpeg.filter([seg_a.video, seg_b.video], 'xfade', transition='fade', duration=xfade, offset=dur_a-xfade)
            a_merged = ffmpeg.filter([seg_a.audio, seg_b.audio], 'acrossfade', d=xfade)
            
            ffmpeg.output(v_merged, a_merged, output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', crf=21).run(overwrite_output=True, quiet=True)

        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✓ Rank {rank} completato.")
        return True

    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        print(f"✗ Errore Rank {rank}: {e}")
        return False

if __name__ == "__main__":
    cfg = load_config()
    d_cfg = cfg['download_config']
    os.makedirs(d_cfg['output_dir'], exist_ok=True)
    os.makedirs(d_cfg['temp_dir'], exist_ok=True)
    
    df = pd.read_excel(cfg['excel_file'])
    u_col_idx = column_index_from_string(d_cfg['url_col']) - 1
    r_col_idx = column_index_from_string(d_cfg['rank_col']) - 1
    
    for _, row in df.iterrows():
        url, rank = row.iloc[u_col_idx], row.iloc[r_col_idx]
        if pd.isna(url) or pd.isna(rank): continue
        process_video(url, int(rank))