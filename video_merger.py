import os
import json
import pandas as pd
from openpyxl.utils import column_index_from_string

# Gestione import per compatibilità MoviePy 2.0+
try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

def load_config():
    """Carica la configurazione dal file JSON."""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_files_for_rank(rank, clips_dir, cards_dir):
    """Trova il video e la card corrispondenti al Rank specificato."""
    video_file = None
    card_file = None
    
    video_path = os.path.join(clips_dir, f"{rank}_clip.mp4")
    if os.path.exists(video_path):
        video_file = video_path
        
    if os.path.exists(cards_dir):
        for f in os.listdir(cards_dir):
            if f.startswith(f"{rank}_") and f.endswith(".png"):
                card_file = os.path.join(cards_dir, f)
                break
            
    return video_file, card_file

def merge_videos():
    cfg = load_config()
    d_cfg = cfg['download_config']
    c_cfg = cfg['card_config']
    e_cfg = cfg['video_editor_config']
    
    output_dir = e_cfg['output_final_dir']
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        df = pd.read_excel(cfg['excel_file'])
    except Exception as e:
        print(f"Errore caricamento Excel: {e}")
        return

    rank_col_name = c_cfg['fields']['Rank Number']['col']
    
    for index, row in df.iterrows():
        rank = row.iloc[column_index_from_string(rank_col_name) - 1]
        video_path, card_path = get_files_for_rank(rank, d_cfg['output_dir'], c_cfg['output_folder'])
        
        if not video_path or not card_path:
            continue

        print(f"🎬 Elaborazione Rank {rank}...")

        try:
            video = VideoFileClip(video_path)
            
            target_w, target_h = e_cfg['video_size']
            extra_zoom = e_cfg.get('video_zoom', 1.0)
            
            # --- LOGICA DI SCALATURA (FILL) ---
            scale_w = target_w / video.w
            scale_h = target_h / video.h
            final_scale = max(scale_w, scale_h) * extra_zoom
            video_scaled = video.resized(final_scale)

            # --- CENTRATURA RISPETTO AL RIQUADRO ---
            offset_x = tuple(e_cfg['video_position'])[0] - (video_scaled.w - target_w) / 2
            offset_y = tuple(e_cfg['video_position'])[1] - (video_scaled.h - target_h) / 2

            # --- LOGICA OVERLAY (CARD) ---
            overlay = (ImageClip(card_path)
                       .with_duration(video.duration)
                       .with_position((0, 0)))

            # --- COMPOSIZIONE ---
            final_clip = CompositeVideoClip(
                [
                    video_scaled.with_position((offset_x, offset_y)), 
                    overlay
                ],
                size=overlay.size
            )

            # --- ESPORTAZIONE ---
            output_filename = os.path.basename(card_path).replace(".png", ".mp4")
            final_path = os.path.join(output_dir, output_filename)
            
            # DEFINIZIONE PERCORSO FILE AUDIO TEMPORANEO
            # Lo salviamo nella stessa cartella di output del video
            temp_audio_path = os.path.join(output_dir, f"temp_audio_{rank}.m4a")
            
            final_clip.write_videofile(
                final_path, 
                codec="libx264", 
                audio_codec="aac", 
                fps=e_cfg['fps'],
                temp_audiofile=temp_audio_path, # <--- Modifica qui
                remove_temp=True,               # Assicura che venga rimosso dopo l'uso
                logger=None
            )
            
            video.close()
            final_clip.close()
            print(f"✓ Creato: {output_filename}")

        except Exception as e:
            print(f"✗ Errore Rank {rank}: {e}")

if __name__ == "__main__":
    merge_videos()