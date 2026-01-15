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
        # Caricamento clip video originale
        video = VideoFileClip(v_path, audio=True)
        tw, th = e_cfg['video_size']
        zoom = e_cfg.get('video_zoom', 1.0)
        
        # Recupero modalità di ridimensionamento dal config (default: crop per compatibilità)
        resize_mode = e_cfg.get('resize_mode', 'crop')

        # CALCOLO SCALA (Scale)
        if resize_mode == 'letterbox':
            # LETTERBOX: Il video sta tutto dentro, avanzano bande nere (usa MIN)
            scale = min(tw / video.w, th / video.h) * zoom
        else:
            # CROP: Il video riempie tutto il riquadro e viene tagliato (usa MAX)
            scale = max(tw / video.w, th / video.h) * zoom
        
        v_scaled = video.resized(scale)
        
        # CALCOLO POSIZIONE (Centramento)
        # Calcoliamo lo scostamento necessario per centrare il video ridimensionato rispetto al target
        center_x = (tw - v_scaled.w) / 2
        center_y = (th - v_scaled.h) / 2
        
        # ox e oy sommano la posizione fissa del config al centramento dinamico
        ox = e_cfg['video_position'][0] + center_x
        oy = e_cfg['video_position'][1] + center_y

        # Caricamento Overlay (la card grafica PNG)
        overlay = ImageClip(c_path).with_duration(video.duration).with_position((0, 0))
        
        # Composizione finale: 
        # - Lo sfondo del CompositeVideoClip è nero, creando automaticamente le bande se in letterbox
        # - size=(tw, th) definisce la risoluzione finale (es. 1080x1920)
        final_clip = CompositeVideoClip(
            [v_scaled.with_position((ox, oy)), overlay], 
            size=(tw, th)
        )

        out_name = os.path.basename(c_path).replace(".png", ".mp4")
        final_path = os.path.join(e_cfg['output_final_dir'], out_name)
        temp_audio = os.path.join(e_cfg['output_final_dir'], f"temp_audio_{rank}.m4a")

        # Scrittura del file video (Rendering)
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
        
        # Pulizia risorse
        video.close()
        final_clip.close()

        # NORMALIZZAZIONE AUDIO (Mastering Finale post-rendering)
        if e_cfg.get('audio_normalization', {}).get('enabled'):
            sys.stdout.write(f"🔊 [Rank {rank}] LOG: Normalizzazione audio in corso...\n")
            sys.stdout.flush()
            normalize_final_clip(final_path, e_cfg)

        sys.stdout.write(f"\n✅ [Rank {rank}] COMPLETATO: {out_name}\n")
        sys.stdout.flush()
        return {"Rank": rank, "Status": "OK", "File": out_name}

    except Exception as e:
        sys.stdout.write(f"\n❌ [Rank {rank}] ERRORE: {str(e)}\n")
        sys.stdout.flush()
        return {"Rank": rank, "Status": "Error", "File": None}

def main():
    # Caricamento configurazioni globali
    cfg = load_config()
    g_cfg = cfg['global_settings']
    m_cfg = cfg['excel_mapping']
    d_cfg = cfg['download_config']
    c_cfg = cfg['card_config']
    e_cfg = cfg['video_editor_config']

    os.makedirs(e_cfg['output_final_dir'], exist_ok=True)
    
    # Lettura Excel per recuperare i Rank da processare
    df = pd.read_excel(g_cfg['excel_file'])
    
    tasks = []
    for _, row in df.iterrows():
        rank = row.iloc[column_index_from_string(m_cfg['rank_col']) - 1]
        v_path = os.path.join(d_cfg['output_dir'], f"{rank}_clip.mp4")
        
        # Controllo esistenza file e integrità (no 0 byte)
        if not os.path.exists(v_path) or os.path.getsize(v_path) == 0:
            continue
            
        # Ricerca della card PNG corrispondente al Rank
        c_path = next((os.path.join(c_cfg['output_folder'], f) for f in (os.listdir(c_cfg['output_folder']) if os.path.exists(c_cfg['output_folder']) else []) if f.startswith(f"{rank}_")), None)
        
        if v_path and c_path:
            tasks.append((rank, v_path, c_path, e_cfg))

    # Gestione Multi-Processing
    max_workers = g_cfg.get('max_workers', 2)
    print(f"🎬 [MERGE SYSTEM] Avvio {max_workers} processi simultanei (Modo: {e_cfg.get('resize_mode', 'crop')})...")

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

    # Salvataggio report finale
    if results:
        reports_dir = os.path.dirname(e_cfg.get('output_final_dir', 'output/final_videos')) or 'output'
        os.makedirs(reports_dir, exist_ok=True)
        merge_report_path = os.path.join(reports_dir, 'merge_report.csv')
        pd.DataFrame(results).to_csv(merge_report_path, index=False)
        print(f"\n✨ Procedura terminata. Report salvato: {merge_report_path}")

if __name__ == "__main__":
    main()