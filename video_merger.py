import os
import pandas as pd
import multiprocessing
from openpyxl.utils import column_index_from_string
import time
import sys

try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

from modules.config_loader import load_config
from modules.audio_processor import normalize_final_clip

def merge_worker(task_data):
    rank, v_path, c_path, e_cfg = task_data
    sys.stdout.write(f"\n[Rank {rank}] -> Inizio Rendering...\n")
    sys.stdout.flush()
    
    try:
        video = VideoFileClip(v_path, audio=True)
        tw, th = e_cfg['video_size']
        zoom = e_cfg.get('video_zoom', 1.0)
        
        scale = max(tw / video.w, th / video.h) * zoom
        v_scaled = video.resized(scale)
        
        ox = e_cfg['video_position'][0] - (v_scaled.w - tw) / 2
        oy = e_cfg['video_position'][1] - (v_scaled.h - th) / 2

        overlay = ImageClip(c_path).with_duration(video.duration).with_position((0, 0))
        final_clip = CompositeVideoClip([v_scaled.with_position((ox, oy)), overlay], size=overlay.size)

        out_name = os.path.basename(c_path).replace(".png", ".mp4")
        final_path = os.path.join(e_cfg['output_final_dir'], out_name)
        temp_audio = os.path.join(e_cfg['output_final_dir'], f"temp_audio_{rank}.m4a")

        # 1. Scrittura del video tramite MoviePy
        final_clip.write_videofile(
            final_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=e_cfg['fps'],
            temp_audiofile=temp_audio,
            remove_temp=True,
            logger='bar',
            threads=1,
            preset="ultrafast"
        )
        
        video.close()
        final_clip.close()

        # 2. NORMALIZZAZIONE AUDIO (Mastering Finale)
        if e_cfg.get('audio_normalization', {}).get('enabled'):
            sys.stdout.write(f"🔊 [Rank {rank}] LOG: Normalizzazione audio in corso...\n")
            sys.stdout.flush()
            # Passiamo d_cfg o e_cfg (basta che contenga la chiave audio_normalization)
            normalize_final_clip(final_path, e_cfg)

        sys.stdout.write(f"\n✅ [Rank {rank}] COMPLETATO E LIVELLATO: {out_name}\n")
        sys.stdout.flush()
        return {"Rank": rank, "Status": "OK", "File": out_name}

    except Exception as e:
        sys.stdout.write(f"\n❌ [Rank {rank}] ERRORE: {str(e)}\n")
        sys.stdout.flush()
        return {"Rank": rank, "Status": "Error", "File": None}

def main():
    cfg = load_config()
    g_cfg = cfg['global_settings']
    m_cfg = cfg['excel_mapping']
    d_cfg = cfg['download_config']
    c_cfg = cfg['card_config']
    e_cfg = cfg['video_editor_config']

    os.makedirs(e_cfg['output_final_dir'], exist_ok=True)
    df = pd.read_excel(g_cfg['excel_file'])
    
    tasks = []
    for _, row in df.iterrows():
        rank = row.iloc[column_index_from_string(m_cfg['rank_col']) - 1]
        v_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")
        c_path = next((os.path.join(c_cfg['output_folder'], f) for f in (os.listdir(c_cfg['output_folder']) if os.path.exists(c_cfg['output_folder']) else []) if f.startswith(f"{rank}_")), None)
        if v_path and c_path and os.path.exists(v_path):
            tasks.append((rank, v_path, c_path, e_cfg))

    # Per evitare flickering eccessivo, non superare i 2-3 worker
    max_workers = g_cfg.get('max_workers', 2)
    print(f"🎬 [MERGE SYSTEM] Avvio {max_workers} processi simultanei...")

    pool = multiprocessing.Pool(processes=max_workers)
    results = []

    try:
        async_results = [pool.apply_async(merge_worker, (t,)) for t in tasks]
        
        while len(results) < len(tasks):
            for i, r in enumerate(async_results):
                if r is not None and r.ready():
                    results.append(r.get())
                    async_results[i] = None
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 [STOP] Interruzione immediata!")
        pool.terminate()
        pool.join()
        os._exit(1)
    finally:
        pool.close()
        pool.join()

    if results:
        # Ensure top-level output folder exists and save merge report there
        reports_dir = os.path.dirname(e_cfg.get('output_final_dir', 'output/final_videos')) or 'output'
        os.makedirs(reports_dir, exist_ok=True)
        merge_report_path = os.path.join(reports_dir, 'merge_report.csv')
        pd.DataFrame(results).to_csv(merge_report_path, index=False)
        print(f"\n✨ Procedura terminata. Report salvato: {merge_report_path}")

if __name__ == "__main__":
    main()