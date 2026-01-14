# RANKINATOR
Automatic party ranking video/card generator

## Overview
RANKINATOR automates: downloading clip segments, generating graphic cards, and merging video into final layouts for a party ranking or chart.

## Requirements
- Python 3.8 or newer
- FFmpeg (must be on `PATH`)
- Optional: Deno (some helper scripts may use it)

## Installation (Windows)
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install Python dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Install FFmpeg and add it to your system `PATH` (official builds or from https://www.gyan.dev/ffmpeg/builds/).

4. (Optional) Install Deno on Windows (if needed):

```powershell
iwr https://deno.land/install.ps1 -useb | iex
```

## Configuration
All runtime settings are in `config.json`. A detailed guide is available at [SETTINGS_GUIDE.md](SETTINGS_GUIDE.md).

This README also explains each top-level entry from `config.json`:

- **`global_settings`**
	- `excel_file`: path to the Excel spreadsheet with dataset (votes, titles, URLs).
	- `font_path`: font filename or path used when drawing text (e.g. `comic.ttf`).
	- `max_workers`: maximum parallel workers for CPU-bound tasks (download/processing).

- **`excel_mapping`**
	- Columns mapping for the Excel file:
		- `rank_col`, `notes_col`, `category_col`, `title_col`, `author_col`, `origin_col`, `timestamp_col`, `url_col`, `average_col` — Excel column letters used by the scripts.
	- `voters_map_group1` / `voters_map_group2`: mappings of voter names to Excel columns (used when rendering voter scores on cards).

- **`download_config`**
	- `output_dir`: where downloaded clips are stored (default `output/clips`).
	- `temp_dir`: temporary files (default `output/temp`).
	- `failed_log`: CSV path where failed download URLs are logged.
	- `default_duration`: default total clip duration (seconds) if not specified by rank.
	- `default_split_percentage`: fallback split ratio between intro/highlight.
	- `duration_map`: per-rank ranges controlling `total` seconds and `split` ratio.
	- `crossfade_duration`: seconds of crossfade when joining intro+highlight.
	- `heatmap_limit`: threshold used when selecting highlight region from audio heatmap.
	- `before_highlight_offset`: seconds to include before detected highlight.
	- `silence_threshold`: audio threshold for silence detection (e.g. `-45dB`).
	- `silence_duration`: minimum silence length (seconds) to be considered.
	- `chorus_percentage`: fallback percentage position to search for chorus when heatmap is absent.

- **`card_config`**
	- `base_image`: template image used as background for generated cards.
	- `output_folder`: where generated card images are saved.
	- `icons_directory`: directory containing category icons.
	- `icon_coord`: pixel coordinate where the category icon is pasted.
	- `hidden_categories`: categories that should not display an icon (e.g. `Intro`).
	- `voters_ui`: visual settings for voter blocks:
		- `font_size`, `border_width`, `border_color` (RGB), `y_offset` (vertical spacing), `group1_start` / `group2_start` (start coordinates), `colors` (`base`, `max`, `min` RGB values used to color scores).

- **`icons_map`**
	- Mapping of category keys to icon filenames inside `resources/icons/`.

- **`video_editor_config`**
	- `output_final_dir`: directory for final merged videos.
	- `fps`: output frames per second.
	- `video_position`: top-left pixel where the video is placed on the card background.
	- `video_size`: size in pixels of the video area (width, height).
	- `video_zoom`: scaling factor for the video (1.0 = fit exactly).

For a more complete walkthrough and examples for each field, see [SETTINGS_GUIDE.md](SETTINGS_GUIDE.md).

## Usage
Run the main steps (activate your virtualenv first):

```powershell
# Download video segments referenced by the Excel file
python download_clips.py

# Generate graphic cards from the Excel data
python create_cards.py

# Merge clips into the cards to produce final videos
python video_merger.py
```

Outputs are written under the `output/` tree (`clips/`, `cards/`, `final_videos/`).

## Troubleshooting
- Check `output/failed_urls.csv` for download failures.
- If text is missing or misaligned, adjust coordinates in `card_config` within `config.json` or consult [SETTINGS_GUIDE.md](SETTINGS_GUIDE.md).

## Contributing
Submit issues or PRs; keep changes focused and test locally.

---
Generated README — see the settings guide for detailed examples: [SETTINGS_GUIDE.md](SETTINGS_GUIDE.md)