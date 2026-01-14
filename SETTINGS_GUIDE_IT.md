# GUIDA ALLE IMPOSTAZIONI (dettagliata)

Questa è la versione italiana completa della guida alle impostazioni. Spiega le voci di `config.json` con esempi pratici, comandi FFmpeg utili e suggerimenti per il debug.

---

## 1) File Excel (layout e mappatura)

I script leggono il file Excel indicato in `global_settings.excel_file`. Una riga di intestazione tipica può essere:

| A | B | C | D | E | F | G | H | I | J |
|---:|---|---|---|---|---|---|---|---|---|
| rank | notes | category | title | author | origin | timestamp | url | (unused) | average |

Esempi:

- `rank`: posizione in classifica (1, 2, 3...)
- `url`: link YouTube (o id) usato per scaricare il video

Personalizza le colonne nella sezione `excel_mapping` di `config.json` se il tuo file usa colonne diverse.

Esempio di `excel_mapping`:

```json
"excel_mapping": {
  "rank_col": "A",
  "title_col": "D",
  "author_col": "E",
  "url_col": "H"
}
```

I `voters_map_group1` e `voters_map_group2` mappano i nomi dei votanti alle colonne Excel che contengono i loro voti.

---

## 2) `download_config` — download e selezione segmenti

Scopo: definire la durata dei clip estratti, come individuare i momenti salienti e come unire "intro" e "highlight".

Campi principali con esempi:

- `default_duration`: 30 (secondi)
- `default_split_percentage`: 0.5 (intro 50% / highlight 50%)
- `duration_map`: regole per intervalli di rank. Esempio:

```json
"duration_map": {
  "1-3": {"total": 100, "split": 0.4},
  "4-10": {"total": 40, "split": 0.3}
}
```

Significato: per i rank 1–3 prendi 100s totali e dividi 40% intro (40s) / 60% highlight (60s).

Selezione highlight e heatmap:
- `heatmap_limit` (0.0–1.0): soglia per scegliere la regione ad alta energia
- `before_highlight_offset`: secondi da aggiungere prima dell'inizio dell'highlight rilevato
- `chorus_percentage`: posizione di fallback per cercare il ritornello (es. 0.25 = 25% della durata)

Rilevamento silenzio (esempio FFmpeg)

Usa FFmpeg per individuare silenzi lunghi — utile per evitare regioni vuote:

```bash
ffmpeg -i input.mp4 -af silencedetect=noise=-45dB:d=0.5 -f null -
```

Il comando stampa gli eventi di silenzio; gli script usano logiche simili per non scegliere segmenti silenziosi.

Esempio di crossfade: quando unisci intro e highlight è utile applicare una piccola dissolvenza incrociata. `crossfade_duration` è in secondi (es. 1.0).

---

## 3) `card_config` — layout immagine e testo

Campi e consigli pratici:

- `base_image`: percorso del template PNG su cui disegnare.
- `icon_coord`: `[x, y]` posizione in pixel dove incollare l'icona della categoria (origine in alto a sinistra).
- `hidden_categories`: nomi di categorie che non devono mostrare icona.

Esempio `voters_ui` (parziale):

```json
"voters_ui": {
  "font_size": 40,
  "border_width": 3,
  "y_offset": 103,
  "group1_start": [1435, 80],
  "group2_start": [1727, 80]
}
```

Come regolare rapidamente le coordinate:

1. Apri `base_image` in un editor grafico e attiva i righelli in pixel.
2. Modifica il valore `x` di `group1_start` per spostare orizzontalmente; `y` per spostare verticalmente.
3. `y_offset` controlla la distanza verticale tra i votanti.

I campi di testo (titolo, autore) sono gestiti da coordinate e dimensione del font. Se il testo esce dall'area, riduci `font_size` o troncalo nel codice.

---

## 4) `icons_map` e gestione icone

Associa la chiave della categoria (valore della colonna `category` nell'Excel) al nome del file icona dentro `resources/icons`:

```json
"icons_map": {}
```

Se un'icona manca, lo script può ignorarla o segnalare un errore a seconda del percorso eseguito: verifica eventuali log `output/failed_icons.log`.

---

## 5) `video_editor_config` — inserire il video nella card

- `video_position`: `[x, y]` dell'angolo in alto a sinistra dell'area video sulla card.
- `video_size`: `[width, height]` dimensione esatta dell'area in pixel.
- `video_zoom`: `1.0` adatta perfettamente; `>1.0` ingrandisce ritagliando i bordi.

Se il video appare troppo ritagliato, prova a ridurre `video_zoom` o modificare `video_size`.

---

## 6) Esempio minimale di `config.json` (riferimento)

```json
{
  "global_settings": { "excel_file": "resources/dataset/dataset2.xlsx", "font_path": "comic.ttf", "max_workers": 3 },
  "download_config": { "output_dir": "output/clips", "default_duration": 30, "crossfade_duration": 1.0 },
  "card_config": { "base_image": "resources/template/template.png", "output_folder": "output/cards" }
}
```

---

## 7) Debug pratico e suggerimenti

- Download falliti: apri `output/failed_urls.csv` e riprova a eseguire `download_clips.py` per le righe fallite.
- Controlla `output/temp/` per file temporanei se fallisce l'analisi audio o il merge.
- Aumenta `max_workers` con cautela: molte connessioni contemporanee possono causare rate limit o carico eccessivo.

Comandi FFmpeg utili:

- Informazioni sul file:

```bash
ffmpeg -i input.mp4
```

- Estrarre l'audio in WAV per analisi:

```bash
ffmpeg -i input.mp4 -vn -ac 1 -ar 22050 output.wav
```

---

## 8) Estendere il comportamento

- Per cambiare la logica di ricerca degli highlight, controlla `modules/audio_analyzer.py` e modifica le soglie.
- Per modificare la generazione delle immagini (font, allineamenti) guarda `modules/utils.py` e le funzioni usate da `create_cards.py`.

---

Se vuoi, posso aggiungere un esempio Excel o creare lo script `scripts/print_config.py` che carica `config.json` e stampa i valori effettivi per una verifica rapida.
