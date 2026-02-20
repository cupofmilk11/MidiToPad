
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.abspath("."))

from src.soundpad.client import SoundpadClient

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

print("Initializing SoundpadClient...")
client = SoundpadClient()
# INCREASE CHUNK SIZE FIX
client.remote.chuck_size = 1024 * 1024 # 1MB

print(f"Connecting... (is_alive={client.remote.is_alive()})")
if client.connect():
    print("Connected!")
    print("Fetching sound list...")
    try:
        response = client.remote.get_sound_list()
        print(f"Response Type: {type(response)}")
        if response:
            try:
                print(f"Response Length: {len(response)}")
                preview = response[:500] if isinstance(response, str) or isinstance(response, bytes) else str(response)[:500]
                print(f"Response Preview: {preview}")
            except:
                print("Could not get length/preview")
        else:
            print("Response is None or Empty")
            
        print("Parsing...")
        sounds = client.get_sound_list()
        print(f"Parsed Sounds Count: {len(sounds)}")
        if sounds:
            print(f"First 5 sounds: {sounds[:5]}")
    except Exception as e:
        print(f"Error calling get_sound_list: {e}")
else:
    print("Failed to connect.")
