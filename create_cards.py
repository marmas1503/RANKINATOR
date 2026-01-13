import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import re
from openpyxl.utils import column_index_from_string

# --- 1. FIXED COLUMNS CONFIGURATION ---
FIXED_CONFIG = {
    'Rank Number': {'col': 'A', 'coord': (140, 843), 'size': 66, 'color': (255, 255, 255)},
    'Average':     {'col': 'I', 'coord': (196, 961), 'size': 32, 'color': (255, 255, 255)}, 
    'Title':       {'col': 'D', 'coord': (432, 827), 'size': 40, 'color': (255, 255, 255)},
    'Author':      {'col': 'E', 'coord': (424, 881), 'size': 30, 'color': (255, 255, 255)}, 
    'Origin':      {'col': 'F', 'coord': (424, 925), 'size': 30, 'color': (255, 255, 255)},
    'Notes':       {'col': 'B', 'coord': (308, 967), 'size': 30, 'color': (255, 251, 0)},
}

CATEGORY_COLUMN = 'C' 
HIDDEN_CATEGORIES = ['Drama', 'Mystery'] 

# --- 2. VOTERS CONFIGURATION ---
VOTE_COLOR_BASE = (255, 255, 255) 
VOTE_COLOR_MAX  = (0, 180, 0)   
VOTE_COLOR_MIN  = (255, 50, 50) 
VOTERS_FONT_SIZE = 40

# --- NEW: BORDER SETTINGS ---
VOTE_BORDER_COLOR = (0, 0, 0) # Black
VOTE_BORDER_WIDTH = 3         # Set border thickness here (0 for no border)

VOTERS_MAP = []
group1_names = ["marmas", "selfie veloce", "masterone", "mizzica", "pezzente", "ribery", "john kaminaisi", "airu", "salealberto", "the xeno"]
group1_cols = ["J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"] 

for i, name in enumerate(group1_names):
    VOTERS_MAP.append({'name': name, 'col': group1_cols[i], 'coord': (1435, 80 + (i * 103))})

group2_names = ["pete", "fuschio", "er gooning", "just", "cole", "renato", "bronsa", "godeleti", "grok"]
group2_cols = ["T", "U", "V", "W", "X", "Y", "Z", "AA", "AB"]

for i, name in enumerate(group2_names):
    VOTERS_MAP.append({'name': name, 'col': group2_cols[i], 'coord': (1727, 80 + (i * 103))})

# --- 3. CATEGORY ICONS ---
ICONS_DIRECTORY = 'resources/icons/'
ICONS_MAP = {
    'OST_videogame': 'OST_videogame.png',
}
ICON_COORD = (1115, 830)

# --- 4. GENERAL SETTINGS ---
EXCEL_FILE = 'resources/dataset/dataset.xlsx'
BASE_IMAGE = 'resources/template/template.png'
OUTPUT_FOLDER = 'output/cards'
FONT_PATH = 'comic.ttf' 

if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)

def clean_vote_display(value):
    try:
        num = float(value)
        return str(int(num)) if num.is_integer() else str(num)
    except:
        return str(value)

def sanitize_filename(rank, title):
    clean_title = re.sub(r'[^a-zA-Z0-9]', '_', str(title))
    clean_title = re.sub(r'_+', '_', clean_title)[:20].strip('_')
    return f"{rank}_{clean_title}"

def generate_images():
    try:
        df = pd.read_excel(EXCEL_FILE, header=0)
    except Exception as e:
        print(f"Error loading Excel: {e}")
        return

    for index, row in df.iterrows():
        img = Image.open(BASE_IMAGE).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        cat_idx = column_index_from_string(CATEGORY_COLUMN) - 1
        current_cat = str(row.iloc[cat_idx]).strip()
        is_hidden = current_cat in HIDDEN_CATEGORIES

        # A. DRAW FIXED TEXTS
        for field, info in FIXED_CONFIG.items():
            col_idx = column_index_from_string(info['col']) - 1
            value = row.iloc[col_idx]
            if is_hidden and field in ['Title', 'Author', 'Origin']:
                text_to_print = "???"
            elif field == 'Average' and pd.notna(value):
                text_to_print = f"{float(value):.3f}"
            else:
                text_to_print = str(value if pd.notna(value) else "")
            
            font = ImageFont.truetype(FONT_PATH, info['size'])
            draw.text(info['coord'], text_to_print, fill=info['color'], font=font)

        # B. VOTE LOGIC (MIN/MAX)
        numeric_votes = []
        for v in VOTERS_MAP:
            v_idx = column_index_from_string(v['col']) - 1
            val = row.iloc[v_idx]
            try:
                if pd.notna(val): numeric_votes.append(float(val))
            except: continue
        
        v_max = max(numeric_votes) if numeric_votes else None
        v_min = min(numeric_votes) if numeric_votes else None

        # C. DRAW VOTERS (WITH BORDER)
        voter_font = ImageFont.truetype(FONT_PATH, VOTERS_FONT_SIZE)
        for v in VOTERS_MAP:
            v_idx = column_index_from_string(v['col']) - 1
            raw_val = row.iloc[v_idx]
            if pd.isna(raw_val): continue

            try:
                vote_float = float(raw_val)
                if vote_float == v_max and v_max != v_min: color = VOTE_COLOR_MAX
                elif vote_float == v_min and v_max != v_min: color = VOTE_COLOR_MIN
                else: color = VOTE_COLOR_BASE
                display_text = clean_vote_display(raw_val)
            except:
                color = VOTE_COLOR_BASE
                display_text = str(raw_val)

            # Added stroke_width and stroke_fill for the border
            draw.text(
                v['coord'], 
                display_text, 
                fill=color, 
                font=voter_font,
                stroke_width=VOTE_BORDER_WIDTH,
                stroke_fill=VOTE_BORDER_COLOR
            )

        # D. CATEGORY ICON
        if current_cat in ICONS_MAP and os.path.exists(ICONS_MAP[current_cat]):
            icon = Image.open(ICONS_MAP[current_cat]).convert("RGBA")
            img.paste(icon, ICON_COORD, icon)

        # E. SAVE
        rank_idx = column_index_from_string(FIXED_CONFIG['Rank Number']['col']) - 1
        title_idx = column_index_from_string(FIXED_CONFIG['Title']['col']) - 1
        filename = sanitize_filename(str(row.iloc[rank_idx]), str(row.iloc[title_idx]))
        img.save(os.path.join(OUTPUT_FOLDER, f"{filename}.png"))
        print(f"Processed row {index+1}: {filename}.png")

if __name__ == "__main__":
    generate_images()