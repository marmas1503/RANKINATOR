import os
import sys
import multiprocessing
import argparse
import pandas as pd # Aggiunto per il report
from modules.config_loader import load_config
from modules.audio_processor import normalize_final_clip

def process_single_file(args):
    """Worker: processa il file e restituisce i dati per il report"""
    file_path, config = args
    filename = os.path.basename(file_path)
    
    result_data = {
        'Filename': filename,
        'Status': 'Success',
        'Error': ''
    }
    
    try:
        sys.stdout.write(f"🔊 Normalizzazione: {filename}\n")
        sys.stdout.flush()
        
        normalize_final_clip(file_path, config)
        return result_data
        
    except Exception as e:
        result_data['Status'] = 'Error'
        result_data['Error'] = str(e)
        return result_data

def main():
    parser = argparse.ArgumentParser(description="Normalizza l'audio dei video e genera un report.")
    parser.add_argument("folder", nargs="?", help="Percorso della cartella contenente i video")
    args = parser.parse_args()

    cfg = load_config()
    e_cfg = cfg.get('video_editor_config', {})
    
    if args.folder:
        target_dir = args.folder
    else:
        target_dir = e_cfg.get('output_final_dir', 'output/final_videos')

    if not os.path.exists(target_dir):
        print(f"❌ Errore: La cartella '{target_dir}' non esiste.")
        return

    video_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith('.mp4')]

    if not video_files:
        print(f"📭 Nessun file .mp4 trovato in: {target_dir}")
        return

    # Creazione cartella report se non esiste
    report_dir = "output/report"
    os.makedirs(report_dir, exist_ok=True)

    print(f"🎬 Cartella target: {target_dir}")
    print(f"🚀 Trovati {len(video_files)} video. Avvio elaborazione...")

    max_workers = cfg.get('global_settings', {}).get('max_workers', 4)
    pool = multiprocessing.Pool(processes=max_workers)
    
    tasks = [(f, e_cfg) for f in video_files]
    
    results_list = []
    try:
        # Eseguiamo i task
        results_list = pool.map(process_single_file, tasks)
        
        # Generazione Report CSV
        report_df = pd.DataFrame(results_list)
        report_path = os.path.join(report_dir, "audio_normalization_report.csv")
        report_df.to_csv(report_path, index=False)
        
        # Stampiamo un breve riepilogo a video
        print("\n--- RISULTATI ---")
        successi = sum(1 for r in results_list if r['Status'] == 'Success')
        errori = sum(1 for r in results_list if r['Status'] == 'Error')
        print(f"✅ Completati: {successi}")
        print(f"❌ Falliti: {errori}")
        print(f"📊 Report salvato in: {report_path}")

    except KeyboardInterrupt:
        print("\n🛑 Interruzione manuale.")
        pool.terminate()
    finally:
        pool.close()
        pool.join()

if __name__ == "__main__":
    main()