import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import json
import re
from openpyxl.utils import column_index_from_string

def load_config():
    """Carica la configurazione dal file JSON."""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def sanitize_filename(rank, title):
    """Pulisce il titolo per renderlo un nome file valido su Windows/Linux."""
    # Sostituisce i caratteri non alfanumerici con underscore
    clean_title = re.sub(r'[^a-zA-Z0-9]', '_', str(title))
    # Rimuove underscore doppi e taglia la lunghezza
    clean_title = re.sub(r'_+', '_', clean_title)[:20].strip('_')
    return f"{rank}_{clean_title}"

def get_voters_list(cfg):
    """Costruisce la lista dei votanti calcolando le coordinate dinamiche."""
    voters = []
    c_cfg = cfg['card_config']
    
    # Processa Gruppo 1
    for i, (name, col) in enumerate(cfg['voters_map_group1'].items()):
        coord = [
            c_cfg['voters']['group1_start'][0], 
            c_cfg['voters']['group1_start'][1] + (i * c_cfg['voters']['y_offset'])
        ]
        voters.append({'name': name, 'col': col, 'coord': coord})
        
    # Processa Gruppo 2
    for i, (name, col) in enumerate(cfg['voters_map_group2'].items()):
        coord = [
            c_cfg['voters']['group2_start'][0], 
            c_cfg['voters']['group2_start'][1] + (i * c_cfg['voters']['y_offset'])
        ]
        voters.append({'name': name, 'col': col, 'coord': coord})
    return voters

def generate_images():
    # 1. Inizializzazione
    cfg = load_config()
    c_cfg = cfg['card_config']
    v_set = c_cfg['voters']
    
    if not os.path.exists(c_cfg['output_folder']):
        os.makedirs(c_cfg['output_folder'])
        
    try:
        df = pd.read_excel(cfg['excel_file'])
    except Exception as e:
        print(f"Errore caricamento Excel: {e}")
        return

    voters = get_voters_list(cfg)

    # 2. Elaborazione righe
    for index, row in df.iterrows():
        # Carica template
        img = Image.open(c_cfg['base_image']).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Gestione Categorie e Visibilità
        cat_col_idx = column_index_from_string(c_cfg['category_col']) - 1
        current_cat = str(row.iloc[cat_col_idx]).strip()
        is_hidden = current_cat in c_cfg['hidden_categories']

        # A. DISEGNO CAMPI FISSI (Rank, Titolo, Autore, ecc.)
        for field, info in c_cfg['fields'].items():
            col_idx = column_index_from_string(info['col']) - 1
            val = row.iloc[col_idx]
            
            # Logica "???" per categorie nascoste
            if is_hidden and field in ['Title', 'Author', 'Origin']:
                text_to_print = "???"
            elif field == 'Average' and pd.notna(val):
                text_to_print = f"{float(val):.3f}"
            else:
                text_to_print = str(val if pd.notna(val) else "")
            
            font = ImageFont.truetype(cfg['font_path'], info['size'])
            draw.text(tuple(info['coord']), text_to_print, fill=tuple(info['color']), font=font)

        # B. LOGICA VOTI (Min/Max e Colori)
        numeric_votes = []
        for v in voters:
            v_idx = column_index_from_string(v['col']) - 1
            val = row.iloc[v_idx]
            try:
                if pd.notna(val): numeric_votes.append(float(val))
            except: continue
        
        v_max = max(numeric_votes) if numeric_votes else None
        v_min = min(numeric_votes) if numeric_votes else None

        # C. DISEGNO VOTANTI
        voter_font = ImageFont.truetype(cfg['font_path'], v_set['font_size'])
        for v in voters:
            v_idx = column_index_from_string(v['col']) - 1
            raw_val = row.iloc[v_idx]
            if pd.isna(raw_val): continue

            # Determina colore
            color = tuple(v_set['colors']['base'])
            try:
                vote_float = float(raw_val)
                if v_max != v_min:
                    if vote_float == v_max: color = tuple(v_set['colors']['max'])
                    elif vote_float == v_min: color = tuple(v_set['colors']['min'])
                
                # Formattazione numero (rimuove .0)
                display_text = str(int(vote_float)) if vote_float.is_integer() else str(vote_float)
            except:
                display_text = str(raw_val)

            draw.text(
                tuple(v['coord']), 
                display_text, 
                fill=color, 
                font=voter_font,
                stroke_width=v_set['border_width'],
                stroke_fill=tuple(v_set['border_color'])
            )

        # D. ICONA CATEGORIA
        if current_cat in cfg['icons_map']:
            icon_path = os.path.join(c_cfg['icons_directory'], cfg['icons_map'][current_cat])
            if os.path.exists(icon_path):
                icon = Image.open(icon_path).convert("RGBA")
                img.paste(icon, tuple(c_cfg['icon_coord']), icon)

        # E. SALVATAGGIO CON SANITIZZAZIONE
        rank_col = c_cfg['fields']['Rank Number']['col']
        title_col = c_cfg['fields']['Title']['col']
        
        rank_val = row.iloc[column_index_from_string(rank_col) - 1]
        title_val = row.iloc[column_index_from_string(title_col) - 1]

        filename = sanitize_filename(rank_val, title_val)
        img.save(os.path.join(c_cfg['output_folder'], f"{filename}.png"))
        print(f"✓ Card generata: {filename}.png")

if __name__ == "__main__":
    generate_images()