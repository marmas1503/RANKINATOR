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

def merge_worker(task_data):
    rank, v_path, c_path, e_cfg = task_data
    sys.stdout.write(f"\n[Rank {rank}] -> Inizio Rendering...\n")
    sys.stdout.flush()
    
    try:
        video = VideoFileClip(v_path, audio=True)
        
        # Dimensioni Target e Area del buco
        tw, th = e_cfg['video_size']
        aw, ah = e_cfg.get('video_area_size', [tw, th]) 
        pos_x, pos_y = e_cfg.get('video_position', [0, 0])
        
        resize_mode = e_cfg.get('resize_mode', 'crop')
        zoom = e_cfg.get('video_zoom', 1.0)
        
        # --- LOGICA DI SCALATURA ---
        if resize_mode == 'letterbox':
            # Forza l'occupazione totale dell'altezza del buco
            scale = (ah / video.h) * zoom
        else:
            # Logica CROP originale (satura tutto lo spazio del buco)
            scale = max(aw / video.w, ah / video.h) * zoom
            
        v_scaled = video.resized(scale)
        
        # --- POSIZIONAMENTO ---
        # Centramento orizzontale e verticale rispetto alle coordinate del buco
        ox = pos_x + (aw - v_scaled.w) / 2
        oy = pos_y + (ah - v_scaled.h) / 2

        overlay = ImageClip(c_path).with_duration(video.duration).with_position((0, 0))
        
        # Composizione: video centrato e card sopra
        final_clip = CompositeVideoClip([
            v_scaled.with_position((ox, oy)), 
            overlay
        ], size=overlay.size)

        out_name = os.path.basename(c_path).replace(".png", ".mp4")
        final_path = os.path.join(e_cfg['output_final_dir'], out_name)
        temp_audio = os.path.join(e_cfg['output_final_dir'], f"temp_audio_{rank}.m4a")

        # Rendering video
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

        sys.stdout.write(f"\n✅ [Rank {rank}] RENDERING COMPLETATO: {out_name}\n")
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
        
        if not os.path.exists(v_path) or os.path.getsize(v_path) == 0:
            continue
            
        c_path = next((os.path.join(c_cfg['output_folder'], f) for f in (os.listdir(c_cfg['output_folder']) if os.path.exists(c_cfg['output_folder']) else []) if f.startswith(f"{rank}_")), None)
        
        if v_path and c_path:
            tasks.append((rank, v_path, c_path, e_cfg))

    max_workers = g_cfg.get('max_workers', 2)
    print(f"🎬 [MERGE SYSTEM] Avvio {max_workers} processi di rendering...")

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
        print("\n🛑 Interruzione manuale.")
        pool.terminate()
        os._exit(1)
    finally:
        pool.close()
        pool.join()

    if results:
        reports_dir = os.path.dirname(e_cfg.get('output_final_dir', 'output/final_videos')) or 'output'
        os.makedirs(reports_dir, exist_ok=True)
        pd.DataFrame(results).to_csv(os.path.join(reports_dir, 'report/merge_report.csv'), index=False)
        print(f"\n✨ Rendering terminato. Ricordati di avviare lo script di normalizzazione audio separato.")

if __name__ == "__main__":
    main()