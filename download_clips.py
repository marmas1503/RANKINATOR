import pandas as pd
import yt_dlp
import ffmpeg
import os

# --- CONFIGURATION ---
EXCEL_FILE = 'dataset.xlsx'
FAILED_LOG_FILE = 'failed_urls.csv'
URL_COL_LETTER = 'G'
RANK_COL_LETTER = 'A'
CLIP_DURATION = 30
BEFORE_HIGHLIGHT = 2
DEFAULT_START_CLIP = 30
OUTPUT_DIR = 'downloaded_clips'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def column_letter_to_index(letter):
    letter = letter.upper()
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1

def process_video(url, rank):
    filename = f"Rank_{rank}.mp4"
    temp_filename = f"temp_{rank}.mp4"
    output_path = os.path.join(OUTPUT_DIR, filename)

    try:
        # 1. Recupero Info e Heatmap
        # Corretto l'errore della stringa 'ejs:github' passandola correttamente
        ydl_opts_meta = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            # Aggiornamento parametri per bypassare i blocchi
            ydl.params['remote_components'] = ['ejs:github'] 
            info = ydl.extract_info(url, download=False)
            heatmap = info.get('heatmap')
            
        start_timestamp = 0
        duration = CLIP_DURATION
        if heatmap:
            peak_moment = max(heatmap, key=lambda x: x['value'])
            start_timestamp = max(0, peak_moment['start_time'] - BEFORE_HIGHLIGHT)
        else:
            duration = DEFAULT_START_CLIP

        # 2. DOWNLOAD FORMATO IBRIDO
        # Chiediamo il miglior MP4 disponibile che contenga già tutto
        ydl_opts_dl = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': temp_filename,
            'quiet': True,
        }
        ydl_opts_dl['remote_components'] = ['ejs:github']

        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
            ydl.download([url])

        if not os.path.exists(temp_filename):
            return False

        # 3. TAGLIO E RE-ENCODING SEMPLIFICATO
        # Riduciamo i parametri all'osso per evitare conflitti di codec
        (
            ffmpeg
            .input(temp_filename, ss=start_timestamp, t=duration)
            .output(output_path, 
                    vcodec='libx264', 
                    acodec='aac', 
                    pix_fmt='yuv420p', # Questo serve per farli vedere su Windows
                    crf=23)
            .run(overwrite_output=True, quiet=True)
        )

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        print(f"✓ Success: {filename}")
        return True

    except Exception as e:
        if os.path.exists(temp_filename): os.remove(temp_filename)
        print(f"✗ Error at Rank {rank}: {e}")
        return False

def main():
    url_idx = column_letter_to_index(URL_COL_LETTER)
    rank_idx = column_letter_to_index(RANK_COL_LETTER)
    failed_videos = []
    
    df = pd.read_excel(EXCEL_FILE)
    
    for _, row in df.iterrows():
        url = row.iloc[url_idx]
        rank = row.iloc[rank_idx]
        if pd.isna(url): continue
        
        print(f"\nProcessing Rank {rank}...")
        if not process_video(url, rank):
            failed_videos.append({'Position': rank, 'URL': url})

    if failed_videos:
        pd.DataFrame(failed_videos).to_csv(FAILED_LOG_FILE, index=False)
        print(f"\nLog: {FAILED_LOG_FILE}")

if __name__ == "__main__":
    main()