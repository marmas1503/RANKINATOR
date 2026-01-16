@echo off
python3 ./create_cards.py
python ./download_clips.py
python ./audio_normalizer.py output/clips
pause