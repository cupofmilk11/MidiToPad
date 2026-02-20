import sys
import os

# Ensure src in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.soundpad.client import SoundpadClient

client = SoundpadClient()
if client.connect():
    # 1. Test get_sound_list raw
    try:
        raw_sounds = client.remote._send_request("GetSoundlist")
        print("--- GetSoundlist RAW ---")
        if raw_sounds:
            print(raw_sounds[:500]) # First 500 chars
    except Exception as e:
        print("GetSoundlist failed:", e)

    # 2. Test get_categories raw
    try:
        raw_cats = client.remote._send_request("GetCategories")
        print("--- GetCategories RAW ---")
        if raw_cats:
            print(raw_cats[:500])
    except Exception as e:
        print("GetCategories failed:", e)
else:
    print("Could not connect to Soundpad.")
