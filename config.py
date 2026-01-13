import os

# --- PATH GENERALI ---
EXCEL_FILE = 'resources/dataset/dataset.xlsx'
FONT_PATH = 'comic.ttf'

# --- CONFIGURAZIONE DOWNLOADER VIDEO ---
DOWNLOAD_CONFIG = {
    'url_col': 'G',
    'rank_col': 'A',
    'clip_duration': 30,
    'before_highlight': 2,
    'default_start': 30,
    'chorus_percentage': 0.25,
    'output_dir': 'output/clips',
    'temp_dir': 'output/temp',
    'failed_log': 'output/failed_urls.csv'
}

# --- CONFIGURAZIONE GENERATORE CARD ---
CARD_CONFIG = {
    'base_image': 'resources/template/template.png',
    'output_folder': 'output/cards',
    'category_col': 'C',
    'icon_coord': (1115, 830),
    'icons_directory': 'resources/icons/',
    'hidden_categories': ['Drama', 'Mystery'],
    'fields': {
        'Rank Number': {'col': 'A', 'coord': (140, 843), 'size': 66, 'color': (255, 255, 255)},
        'Average':     {'col': 'I', 'coord': (196, 961), 'size': 32, 'color': (255, 255, 255)}, 
        'Title':       {'col': 'D', 'coord': (432, 827), 'size': 40, 'color': (255, 255, 255)},
        'Author':      {'col': 'E', 'coord': (424, 881), 'size': 30, 'color': (255, 255, 255)}, 
        'Origin':      {'col': 'F', 'coord': (424, 925), 'size': 30, 'color': (255, 255, 255)},
        'Notes':       {'col': 'B', 'coord': (308, 967), 'size': 30, 'color': (255, 251, 0)},
    },
    'voters': {
        'font_size': 40,
        'border_width': 3,
        'border_color': (0, 0, 0),
        'colors': {
            'base': (255, 255, 255),
            'max': (0, 180, 0),
            'min': (255, 50, 50)
        }
    }
}

# --- MAPPATURA VOTANTI ---
def get_voters_map():
    voters = []
    g1_names = ["marmas", "selfie veloce", "masterone", "mizzica", "pezzente", "ribery", "john kaminaisi", "airu", "salealberto", "the xeno"]
    g1_cols = ["J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"]
    for i, name in enumerate(g1_names):
        voters.append({'name': name, 'col': g1_cols[i], 'coord': (1435, 80 + (i * 103))})

    g2_names = ["pete", "fuschio", "er gooning", "just", "cole", "renato", "bronsa", "godeleti", "grok"]
    g2_cols = ["T", "U", "V", "W", "X", "Y", "Z", "AA", "AB"]
    for i, name in enumerate(g2_names):
        voters.append({'name': name, 'col': g2_cols[i], 'coord': (1727, 80 + (i * 103))})
    return voters

# --- MAPPATURA ICONE ---
ICONS_MAP = {
    'OST_videogame': 'OST_videogame.png',
}