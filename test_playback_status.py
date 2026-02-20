
from src.soundpad.client import SoundpadClient
import time

client = SoundpadClient()
if client.connect():
    print("Connected. Play a sound in Soundpad now...")
    time.sleep(3)
    
    try:
        # Try generic status first
        status = client.get_playback_status()
        print(f"Status: {status}")
        
        # Try raw command if wrapper doesn't support specifics
        # Command "GetPlayStatus" usually returns index? or "Playing"?
        # Command "GetPlaybackPosition"
        
        # Let's see what we can get.
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Not connected.")
