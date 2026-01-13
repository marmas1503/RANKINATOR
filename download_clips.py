import pandas as pd
import yt_dlp
import ffmpeg
import os

# --- CONFIGURATION ---
EXCEL_FILE = 'resources/dataset/dataset.xlsx'
URL_COL_LETTER = 'G'
RANK_COL_LETTER = 'A'
CLIP_DURATION = 30
BEFORE_HIGHLIGHT = 2
DEFAULT_START_CLIP = 30

# Cartelle di Output
BASE_OUTPUT_DIR = 'output'
OUTPUT_CLIPS_DIR = os.path.join(BASE_OUTPUT_DIR, 'clips')
TEMP_DIR = os.path.join(BASE_OUTPUT_DIR, 'temp')
# Il CSV ora viene salvato dentro 'output'
FAILED_LOG_FILE = os.path.join(BASE_OUTPUT_DIR, 'failed_urls.csv')

# Creazione struttura cartelle
for directory in [OUTPUT_CLIPS_DIR, TEMP_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def column_letter_to_index(letter):
    letter = letter.upper()
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1

def process_video(url, rank):
    filename = f"{rank}_clip.mp4"
    temp_filename = os.path.join(TEMP_DIR, f"temp_{rank}.mp4")
    output_path = os.path.join(OUTPUT_CLIPS_DIR, filename)

    try:
        # 1. Recupero Info e Heatmap
        ydl_opts_meta = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
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

        # 3. TAGLIO E RE-ENCODING
        (
            ffmpeg
            .input(temp_filename, ss=start_timestamp, t=duration)
            .output(output_path, 
                    vcodec='libx264', 
                    acodec='aac', 
                    pix_fmt='yuv420p', 
                    crf=23)
            .run(overwrite_output=True, quiet=True)
        )

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        print(f"✓ Successo: {filename}")
        return True

    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        print(f"✗ Errore al Rank {rank}: {e}")
        return False

def main():
    url_idx = column_letter_to_index(URL_COL_LETTER)
    rank_idx = column_letter_to_index(RANK_COL_LETTER)
    failed_videos = []
    
    if not os.path.exists(EXCEL_FILE):
        print(f"Errore: Il file {EXCEL_FILE} non esiste!")
        return

    df = pd.read_excel(EXCEL_FILE)
    
    for _, row in df.iterrows():
        url = row.iloc[url_idx]
        rank = row.iloc[rank_idx]
        if pd.isna(url): continue
        
        print(f"\nElaborazione Rank {rank}...")
        if not process_video(url, rank):
            failed_videos.append({'Position': rank, 'URL': url})

    # Salvataggio CSV nella cartella di output
    if failed_videos:
        pd.DataFrame(failed_videos).to_csv(FAILED_LOG_FILE, index=False, encoding='utf-8-sig')
        print(f"\n--- LOG ERRORI GENERATO ---")
        print(f"File salvato in: {FAILED_LOG_FILE}")
    else:
        # Se esiste un vecchio log di una sessione precedente, lo rimuoviamo per pulizia
        if os.path.exists(FAILED_LOG_FILE):
            os.remove(FAILED_LOG_FILE)
        print("\n--- COMPLETATO: Nessun errore riscontrato! ---")
    
    # Pulizia cartella temp se vuota
    try:
        if os.path.exists(TEMP_DIR) and not os.listdir(TEMP_DIR):
            os.rmdir(TEMP_DIR)
    except:
        pass

if __name__ == "__main__":
    main()