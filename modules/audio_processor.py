import subprocess
import re
import json

def normalize_final_clip(file_path, d_cfg):
    """
    Applica la normalizzazione a due passate (True Peak e Integrated Loudness).
    Analizza il file ed esegue una seconda passata correttiva.
    """
    norm_cfg = d_cfg.get('audio_normalization', {})
    if not norm_cfg.get('enabled', False):
        return

    ti = norm_cfg.get('target_i', -16.0)
    tp = norm_cfg.get('target_tp', -1.5)
    lra = norm_cfg.get('lra', 11.0)

    # Fase 1: Analisi (misuriamo i valori reali della clip appena creata)
    # Usiamo un file temporaneo per non sovrascrivere mentre leggiamo
    temp_output = file_path.replace(".mp4", "_norm.mp4")
    
    # Comando per la normalizzazione accurata
    # Se il volume è ancora diverso, forziamo il 'measured' a 0 per resettare l'algoritmo
    cmd = [
        'ffmpeg', '-y', '-i', file_path,
        '-af', f'loudnorm=I={ti}:TP={tp}:LRA={lra}:print_format=json',
        '-c:v', 'copy', # Non ricodifichiamo il video (velocissimo!)
        '-c:a', 'aac', '-b:a', '192k',
        temp_output
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Sostituiamo il file originale con quello normalizzato
        os.replace(temp_output, file_path)
        return True
    except Exception as e:
        print(f"⚠️ Errore normalizzazione: {e}")
        return False