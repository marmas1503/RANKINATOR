
# ⚙️ Guida alla Configurazione (config.json)

Questa guida spiega come gestire i parametri per il download dei video, la generazione delle card grafiche e il montaggio finale.

---

## 📂 Impostazioni Generali

* **`excel_file`**: Percorso del file Excel contenente i dati (voti, titoli, URL).
* **`font_path`**: Il font utilizzato per tutti i testi (es. `comic.ttf`). Assicurati che il file sia nella cartella principale o specifica il percorso.

---

## 📥 Download Config (`download_config`)

Gestisce come vengono estratti i segmenti video da YouTube.

### ⏱️ Durata e Split (Logica Dual-Clip)

Il sistema scarica due pezzi (Intro + Highlight) e li unisce.

* **`default_duration`**: Durata totale del video se il Rank non è presente nella mappa (30 secondi).
* **`duration_map`**: Regole specifiche per posizione in classifica:
* **Rank 1-3**: 100 secondi totali. Lo `split: 0.4` significa che i primi 40s sono l'inizio della canzone e i restanti 60s sono il ritornello.
* **Rank 4-10**: 40 secondi totali (30% intro / 70% highlight).


* **`crossfade_duration`**: Durata della dissolvenza incrociata tra le due clip (1.0 secondo).

### 🔇 Silence Detection

* **`silence_threshold`**: Soglia di rumore (es. `-60dB`). Più è basso (es. -70), più è sensibile nel trovare il silenzio assoluto.
* **`silence_duration`**: Quanto deve durare il silenzio per essere considerato tale (0.5 secondi).

### 🔗 Mapping Excel

* **`url_col`**: Colonna Excel dove si trovano i link YouTube (Colonna `G`).
* **`rank_col`**: Colonna Excel del numero in classifica (Colonna `A`).
* **`chorus_percentage`**: Se non c'è una "Heatmap" su YouTube, il ritornello viene cercato al 25% della durata del video.

---

## 🎨 Card Config (`card_config`)

Gestisce la creazione dell'immagine overlay (la grafica con i testi).

### 🖼️ Layout Base

* **`base_image`**: Il template grafico (PNG) su cui scrivere.
* **`icon_coord`**: Posizione  dove verrà incollata l'icona della categoria.
* **`hidden_categories`**: Categorie che non mostreranno alcuna icona (es. "Drama").

### ✍️ Campi di Testo (`fields`)

Ogni campo (Titolo, Autore, etc.) ha:

* **`col`**: La colonna Excel da cui leggere il dato.
* **`coord`**: Punto  di inizio scrittura.
* **`size`**: Grandezza del carattere.
* **`color`**: Colore in formato RGB .

### 🗳️ Votanti (`voters`)

Gestisce la lista dei voti che compaiono ai lati o in colonna.

* **`group1_start` / `group2_start**`: Coordinate di partenza per le due colonne di votanti.
* **`y_offset`**: Spazio verticale (103 pixel) tra un votante e quello successivo.
* **`colors`**: Colore dinamico del testo:
* `max`: Colore per il voto più alto (Verde).
* `min`: Colore per il voto più basso (Rosso).



---

## 🎬 Video Editor Config (`video_editor_config`)

Gestisce come il video viene incastrato nella card.

* **`video_position`**: Coordinata  dell'angolo in alto a sinistra del riquadro video nella card (`[41, 105]`).
* **`video_size`**: Dimensione esatta del "buco" trasparente (`1219x688`). Il video verrà scalato per riempire quest'area.
* **`video_zoom`**:
* `1.0`: Il video copre l'area perfettamente.
* `> 1.0`: Ingrandisce ulteriormente il video per tagliare i bordi originali.



---

### 🚀 Note Rapide per modifiche comuni

1. **Spostare un testo**: Cambia i valori in `coord` . Aumentando  vai a destra, aumentando  vai in basso.
2. **Video troppo piccolo/grande**: Regola `video_size` per farlo combaciare con la tua cornice grafica.
3. **Download falliti**: Controlla il file `output/failed_urls.csv` generato automaticamente.

---