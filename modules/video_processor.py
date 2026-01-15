import os
import yt_dlp
import ffmpeg
import time
import subprocess

def download_and_process(url, rank, start_intro, start_highlight, total_dur, dur_a, dur_b, d_cfg, temp_file, output_path):
    xfade = d_cfg.get('crossfade_duration', 1.0)
    fmt = 'bestvideo[ext=mp4][vcodec^=avc1][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    
    start_time_proc = time.time()
    
    # --- CASO 1: CLIP UNICA (Download diretto senza file temporaneo) ---
    if (start_intro + dur_a >= start_highlight):
        print(f"📦 [RANK {rank}] LOG: Modalità CLIP UNICA rilevata.")
        print(f"   > Taglio: da {start_intro:.2f}s per una durata di {total_dur}s")
        
        ydl_opts = {
        'format': fmt, 
        'outtmpl': output_path, 
        'quiet': True,
        'external_downloader': 'ffmpeg',
        'external_downloader_args': {
            'ffmpeg_i': ['-ss', str(start_intro), '-t', str(total_dur)],
            'ffmpeg_o': ['-vcodec', 'libx264', '-acodec', 'aac', '-pix_fmt', 'yuv420p', '-crf', '21']
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # CONTROLLO CRITICO: Il file è valido?
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            print(f"⚠️ [RANK {rank}] Download diretto fallito (SABR/Empty). Passo al metodo robusto...")
            raise Exception("File vuoto")

    except Exception:
        # --- METODO ROBUSTO (DOWNLOAD TEMPORANEO E TAGLIO LOCALE) ---
        # Scarichiamo il pezzo che ci serve localmente senza filtri complessi di yt-dlp
        temp_raw = output_path.replace(".mp4", "_raw.mp4")
        raw_opts = {
            'format': fmt,
            'outtmpl': temp_raw,
            'quiet': True,
            # Non usiamo -ss qui per evitare errori SABR, scarichiamo tutto o usiamo il download nativo
        }
        
        with yt_dlp.YoutubeDL(raw_opts) as ydl:
            ydl.download([url])
        
        # Ora tagliamo il file scaricato localmente con FFmpeg (funziona sempre)
        cmd_cut = [
            'ffmpeg', '-y', '-i', temp_raw,
            '-ss', str(start_intro), '-t', str(total_dur),
            '-vcodec', 'libx264', '-acodec', 'aac', '-pix_fmt', 'yuv420p', '-crf', '21',
            output_path
        ]
        subprocess.run(cmd_cut, capture_output=True)
        
        if os.path.exists(temp_raw):
            os.remove(temp_raw)
    
    # --- CASO 2: CROSSFADE (Download temporaneo + Editing FFmpeg) ---
    else:
        print(f"🎬 [RANK {rank}] LOG: Modalità CROSSFADE rilevata.")
        print(f"   > Segmento A (Intro): {start_intro:.2f}s -> durata {dur_a:.1f}s")
        print(f"   > Segmento B (Highlight): {start_highlight:.2f}s -> durata {dur_b:.1f}s")
        print(f"   > Transizione: {xfade}s")

        # Fase 1: Download file sorgente
        print(f"⏳ [RANK {rank}] LOG: Download del file sorgente temporaneo...")
        with yt_dlp.YoutubeDL({'format': fmt, 'outtmpl': temp_file, 'quiet': True}) as ydl:
            ydl.download([url])
        
        # Fase 2: Rendering FFmpeg
        print(f"⚙️ [RANK {rank}] LOG: Avvio rendering FFmpeg (Crossfade)...")
        render_start = time.time()
        
        try:
            seg_a = ffmpeg.input(temp_file, ss=start_intro, t=dur_a)
            seg_b = ffmpeg.input(temp_file, ss=start_highlight, t=dur_b)
            
            # Filtri Video e Audio
            v = ffmpeg.filter([seg_a.video, seg_b.video], 'xfade', 
                              transition='fade', duration=xfade, offset=dur_a-xfade)
            a = ffmpeg.filter([seg_a.audio, seg_b.audio], 'acrossfade', d=xfade)
            
            (
                ffmpeg.output(v, a, output_path, 
                              vcodec='libx264', acodec='aac', 
                              pix_fmt='yuv420p', crf=21, 
                              preset='veryfast') # preset per velocizzare il render
                .run(overwrite_output=True, quiet=True)
            )
            
            render_end = time.time()
            print(f"✨ [RANK {rank}] LOG: Rendering completato in {render_end - render_start:.2f} secondi.")
            
        except ffmpeg.Error as e:
            print(f"❌ [RANK {rank}] LOG ERRORE FFmpeg: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🧹 [RANK {rank}] LOG: File temporaneo rimosso.")

    total_time = time.time() - start_time_proc
    print(f"🏁 [RANK {rank}] LOG: Processo totale concluso in {total_time:.2f}s.\n")