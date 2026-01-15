# SETTINGS GUIDE (detailed)

This document expands on `config.json` with examples, snippets and practical tips for the download, card generation and video merging steps.

If you only need a quick reference, see the top-level descriptions in `README.md`. This guide walks through: Excel layout, key config sections, FFmpeg examples, and troubleshooting.

---

## 1) Excel dataset (layout and mapping)

The scripts expect an Excel file referenced by `global_settings.excel_file`. Typical header row (columns used in the repo):

| A | B | C | D | E | F | G | H | I | J |
|---:|---|---|---|---|---|---|---|---|---|
| rank | notes | category | title | author | origin | timestamp | url | (unused) | average |

Examples:

- `rank`: integer position (1, 2, 3...)
- `url`: full YouTube URL (or video id) used to download segments

Map each field using `excel_mapping` in `config.json`. If your file uses different columns, change the mapping to match.

Example `excel_mapping` snippet:

```json
"excel_mapping": {
  "rank_col": "A",
  "title_col": "D",
  "author_col": "E",
  "url_col": "H"
}
```

Voter maps (group1 / group2) indicate which column contains each voter's score. Keep the keys as display names and values as the Excel column letters.

---

## 2) `download_config` — download & segment selection

Purpose: how long the extracted clips are, how to find highlights and how to assemble intro + highlight segments.

Key fields with examples:

- `default_duration`: 30
- `default_split_percentage`: 0.5 (intro 50% / highlight 50%)
- `duration_map`: ranges for ranks. Example:

```json
"duration_map": {
  "1-3": {"total": 100, "split": 0.4},
  "4-10": {"total": 40, "split": 0.3}
}
```

Meaning: for ranks 1–3 take 100s total and split 40% intro (40s) / 60% highlight (60s).

Heatmap/highlight selection:
- `heatmap_limit` (0.0–1.0): threshold to pick the top energy region
- `before_highlight_offset`: seconds added before the detected highlight start
- `chorus_percentage`: fallback where to look for chorus (25% means at 25% of video length)

Silence detection (FFmpeg example)

Use FFmpeg to detect long silences — useful to trim leading silence or skip quiet videos:

```bash
ffmpeg -i input.mp4 -af silencedetect=noise=-45dB:d=0.5 -f null -
```

This prints silence start/end events; the scripts use similar logic to avoid choosing silence-only regions.

Crossfade example: when joining intro+highlight, a small crossfade smooths the seam. The `crossfade_duration` is in seconds (e.g. 1.0).

---

## 3) `card_config` — image layout and text

Fields and practical tips:

- `base_image`: path to PNG template. The scripts draw onto this image.
- `icon_coord`: [x, y] pixel where the small category icon is pasted. Coordinates origin is top-left (0,0).
- `hidden_categories`: names that should not get an icon.

Voter UI example (partial):

```json
"voters_ui": {
  "font_size": 40,
  "border_width": 3,
  "y_offset": 103,
  "group1_start": [1435, 80],
  "group2_start": [1727, 80]
}
```

How to adjust coordinates quickly:

1. Open `base_image` in an image editor and enable pixel rulers.
2. Change `group1_start` x value to move horizontally; change y to move vertically.
3. `y_offset` changes spacing between voters.

Text fields (title, author) are controlled by coordinates and font size. If text overflows, reduce `font_size` or truncate string in code.

---

## 4) `icons_map` and icon handling

Map category keys (same as `category` cell in Excel) to a filename in `resources/icons`. Example:

```json
"icons_map": {}
```

If an icon is missing, the script will either skip it or raise an error depending on the code path — check `output/failed_icons.log` if present.

---

## 5) `video_editor_config` — merging video and card

- `video_position`: [x, y] of the top-left corner of the video area on the card.
- `video_size`: [width, height] exact pixel size to scale the video into.
- `video_zoom`: 1.0 fits; >1 crops the edges after scaling.
- `audio_normalization`: settings for normalizing audio levels in the final videos.
  - `enabled`: whether to apply audio normalization (true/false).
  - `target_i`: integrated loudness target (dB, e.g., -14.0).
  - `target_tp`: true peak target (dB, e.g., -1.0).
  - `lra`: loudness range target (dB, e.g., 7.0).

If the video looks cropped incorrectly, try lowering `video_zoom` or adjust `video_size`.

---

## 6) Example minimal `config.json` (reference)

```json
{
  "global_settings": { "excel_file": "resources/dataset/dataset2.xlsx", "font_path": "comic.ttf", "max_workers": 3 },
  "download_config": { "output_dir": "output/clips", "default_duration": 30, "crossfade_duration": 1.0 },
  "card_config": { "base_image": "resources/template/template.png", "output_folder": "output/cards" }
}
```

---

## 7) Practical debugging & tips

- Failed downloads: open `output/failed_urls.csv`. Re-run `download_clips.py` for items that failed.
- Inspect temporary files in `output/temp/` when a merge or audio analysis fails.
- Increase `max_workers` with caution — downloading many clips concurrently can trigger rate limits or CPU overload.

Useful FFmpeg commands:

- Print media info:

```bash
ffmpeg -i input.mp4
```

- Extract audio to WAV for offline analysis:

```bash
ffmpeg -i input.mp4 -vn -ac 1 -ar 22050 output.wav
```

---

## 8) Extending behavior

- To change how highlights are detected, check `modules/audio_analyzer.py` and adjust thresholds there.
- To change image generation (fonts, alignment), edit `modules/utils.py` and the drawing functions used by `create_cards.py`.

---

If you'd like, I can add a small example Excel file, or create a script `scripts/print_config.py` that loads `config.json` and prints resolved values for quick verification.
