import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os, re
from openpyxl.utils import column_index_from_string
import config

c = config.CARD_CONFIG

def sanitize_filename(rank, title):
    clean = re.sub(r'[^a-zA-Z0-9]', '_', str(title))
    return f"{rank}_{clean[:20].strip('_')}"

def generate_images():
    if not os.path.exists(c['output_folder']): os.makedirs(c['output_folder'])
    df = pd.read_excel(config.EXCEL_FILE)
    voters_map = config.get_voters_map()

    for index, row in df.iterrows():
        img = Image.open(c['base_image']).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        cat_val = str(row.iloc[column_index_from_string(c['category_col'])-1]).strip()
        is_hidden = cat_val in c['hidden_categories']

        # A. TESTI FISSI
        for field, info in c['fields'].items():
            val = row.iloc[column_index_from_string(info['col'])-1]
            text = "???" if (is_hidden and field in ['Title', 'Author', 'Origin']) else str(val if pd.notna(val) else "")
            if field == 'Average' and pd.notna(val): text = f"{float(val):.3f}"
            
            font = ImageFont.truetype(config.FONT_PATH, info['size'])
            draw.text(info['coord'], text, fill=info['color'], font=font)

        # B. VOTI
        votes = []
        for v in voters_map:
            val = row.iloc[column_index_from_string(v['col'])-1]
            try: 
                if pd.notna(val): votes.append(float(val))
            except: pass
        
        v_max, v_min = (max(votes), min(votes)) if votes else (None, None)

        for v in voters_map:
            val = row.iloc[column_index_from_string(v['col'])-1]
            if pd.isna(val): continue
            
            color = c['voters']['colors']['base']
            try:
                f_val = float(val)
                if f_val == v_max and v_max != v_min: color = c['voters']['colors']['max']
                elif f_val == v_min and v_max != v_min: color = c['voters']['colors']['min']
                display_txt = str(int(f_val)) if f_val.is_integer() else str(f_val)
            except: display_txt = str(val)

            draw.text(v['coord'], display_txt, fill=color, font=ImageFont.truetype(config.FONT_PATH, c['voters']['font_size']),
                      stroke_width=c['voters']['border_width'], stroke_fill=c['voters']['border_color'])

        # C. ICONA E SALVATAGGIO
        if cat_val in config.ICONS_MAP:
            icon_path = os.path.join(c['icons_directory'], config.ICONS_MAP[cat_val])
            if os.path.exists(icon_path):
                icon = Image.open(icon_path).convert("RGBA")
                img.paste(icon, c['icon_coord'], icon)

        r_val = row.iloc[column_index_from_string(c['fields']['Rank Number']['col'])-1]
        t_val = row.iloc[column_index_from_string(c['fields']['Title']['col'])-1]
        fname = sanitize_filename(r_val, t_val)
        img.save(os.path.join(c['output_folder'], f"{fname}.png"))
        print(f"Card {fname} creata.")

if __name__ == "__main__":
    generate_images()