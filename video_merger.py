import os
import pandas as pd
from openpyxl.utils import column_index_from_string
try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

from modules.config_loader import load_config

def get_files_for_rank(rank, clips_dir, cards_dir):
    video_path = os.path.join(clips_dir, f"{rank}_clip.mp4")
    video_file = video_path if os.path.exists(video_path) else None
    card_file = next((os.path.join(cards_dir, f) for f in os.listdir(cards_dir) 
                      if f.startswith(f"{rank}_") and f.endswith(".png")), None)
    return video_file, card_file

def merge_videos():
    cfg = load_config()
    m_cfg = cfg['excel_mapping']
    d_cfg = cfg['download_config']
    c_cfg = cfg['card_config']
    e_cfg = cfg['video_editor_config']
    
    os.makedirs(e_cfg['output_final_dir'], exist_ok=True)
    df = pd.read_excel(cfg['global_settings']['excel_file'])

    for _, row in df.iterrows():
        rank = row.iloc[column_index_from_string(m_cfg['rank_col']) - 1]
        v_path, c_path = get_files_for_rank(rank, d_cfg['output_dir'], c_cfg['output_folder'])
        
        if not v_path or not c_path: continue
        print(f"🎬 Merging Rank {rank}...")

        try:
            video = VideoFileClip(v_path)
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
            
            final_clip.write_videofile(final_path, codec="libx264", audio_codec="aac", 
                                       fps=e_cfg['fps'], logger=None, remove_temp=True)
            video.close()
            final_clip.close()
            print(f"✓ Creato: {out_name}")
        except Exception as e:
            print(f"✗ Errore Rank {rank}: {e}")

if __name__ == "__main__":
    merge_videos()