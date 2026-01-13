@echo off
python3 ./create_cards.py
python ./download_clips.py
python ./video_merger.py
pause