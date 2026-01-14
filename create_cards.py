import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji
import os
import re
import logging
from openpyxl.utils import column_index_from_string
from modules.config_loader import load_config

# Configurazione Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("generation.log"),
        logging.StreamHandler()
    ]
)

def sanitize_filename(rank, title):
    """Pulisce il titolo per creare un nome file valido."""
    clean_title = re.sub(r'[^a-zA-Z0-9]', '_', str(title))
    clean_title = re.sub(r'_+', '_', clean_title)[:20].strip('_')
    return f"{rank}_{clean_title}"

def get_voters_list(cfg):
    """Mappa i votanti in base alla configurazione Excel."""
    voters = []
    m_cfg = cfg['excel_mapping']
    ui = cfg['card_config']['voters_ui']
    
    for group_name, start_coord in [('voters_map_group1', ui['group1_start']), 
                                    ('voters_map_group2', ui['group2_start'])]:
        for i, (name, col) in enumerate(m_cfg[group_name].items()):
            coord = [start_coord[0], start_coord[1] + (i * ui['y_offset'])]
            voters.append({'name': name, 'col': col, 'coord': coord})
    return voters

def generate_images():
    logging.info("Avvio processo di generazione immagini...")
    
    try:
        cfg = load_config()
        g_cfg = cfg['global_settings']
        m_cfg = cfg['excel_mapping']
        c_cfg = cfg['card_config']
        ui = c_cfg['voters_ui']
        
        os.makedirs(c_cfg['output_folder'], exist_ok=True)
        df = pd.read_excel(g_cfg['excel_file'])
        voters = get_voters_list(cfg)
        logging.info(f"Excel caricato: {len(df)} righe trovate.")
    except Exception as e:
        logging.error(f"Errore durante l'inizializzazione: {e}")
        return

    for index, row in df.iterrows():
        try:
            img = Image.open(c_cfg['base_image']).convert("RGBA")
            
            # Utilizziamo Pilmoji per gestire il rendering delle emoji nel testo
            with Pilmoji(img) as pilmoji_draw:
                
                current_cat = str(row.iloc[column_index_from_string(m_cfg['category_col']) - 1]).strip()
                is_hidden = current_cat in c_cfg['hidden_categories']

                # Campi Dinamici
                fields_to_draw = [
                    (m_cfg['rank_col'], [140, 843], 66, "Rank"),
                    (m_cfg['average_col'], [196, 961], 32, "Average"),
                    (m_cfg['title_col'], [432, 827], 40, "Title"),
                    (m_cfg['author_col'], [424, 881], 30, "Author"),
                    (m_cfg['origin_col'], [424, 925], 30, "Origin"),
                    (m_cfg['notes_col'], [308, 967], 30, "Notes")
                ]

                for col_let, coord, size, f_type in fields_to_draw:
                    val = row.iloc[column_index_from_string(col_let)-1]
                    color = [255, 251, 0] if f_type == "Notes" else [255, 255, 255]
                    
                    if is_hidden and f_type in ["Title", "Author", "Origin"]:
                        text = "???"
                    elif f_type == "Average" and pd.notna(val):
                        text = f"{float(val):.3f}"
                    else:
                        text = str(val if pd.notna(val) else "")

                    font = ImageFont.truetype(g_cfg['font_path'], size)
                    pilmoji_draw.text(tuple(coord), text, fill=tuple(color), font=font)

                # Logica Voti
                numeric_votes = []
                for v in voters:
                    val = row.iloc[column_index_from_string(v['col'])-1]
                    if pd.notna(val): 
                        try: numeric_votes.append(float(val))
                        except: pass
                
                v_max, v_min = (max(numeric_votes), min(numeric_votes)) if numeric_votes else (None, None)
                voter_font = ImageFont.truetype(g_cfg['font_path'], ui['font_size'])

                for v in voters:
                    raw_val = row.iloc[column_index_from_string(v['col'])-1]
                    if pd.isna(raw_val): continue
                    
                    color = tuple(ui['colors']['base'])
                    try:
                        vf = float(raw_val)
                        if v_max != v_min:
                            if vf == v_max: color = tuple(ui['colors']['max'])
                            elif vf == v_min: color = tuple(ui['colors']['min'])
                        display_text = str(int(vf)) if vf.is_integer() else str(vf)
                    except: 
                        display_text = str(raw_val)

                    pilmoji_draw.text(
                        tuple(v['coord']), 
                        display_text, 
                        fill=color, 
                        font=voter_font,
                        stroke_width=ui['border_width'], 
                        stroke_fill=tuple(ui['border_color'])
                    )

            # Inserimento Icona Categoria
            if current_cat in cfg['icons_map']:
                icon_p = os.path.join(c_cfg['icons_directory'], cfg['icons_map'][current_cat])
                if os.path.exists(icon_p):
                    icon = Image.open(icon_p).convert("RGBA")
                    img.paste(icon, tuple(c_cfg['icon_coord']), icon)

            # Salvataggio file
            rank_val = row.iloc[column_index_from_string(m_cfg['rank_col'])-1]
            title_val = row.iloc[column_index_from_string(m_cfg['title_col'])-1]
            fname = sanitize_filename(rank_val, title_val)
            
            output_path = os.path.join(c_cfg['output_folder'], f"{fname}.png")
            img.save(output_path)
            logging.info(f"Card generata con successo: {fname}.png")

        except Exception as e:
            logging.error(f"Errore nella generazione della riga {index}: {e}")

    logging.info("Processo completato.")

if __name__ == "__main__":
    generate_images()