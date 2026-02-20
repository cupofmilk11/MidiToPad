
import logging
from src.soundpad.client import SoundpadClient
import xml.etree.ElementTree as ET

# Setup logging
logging.basicConfig(level=logging.INFO)

client = SoundpadClient()

if client.connect():
    print("Connected to Soundpad")
    
    # 1. Check get_sound_list content
    try:
        raw_response = client.remote.get_sound_list()
        print(f"get_sound_list type: {type(raw_response)}")
        print(f"get_sound_list len: {len(raw_response) if raw_response else 0}")
        print(f"get_sound_list repr: {repr(raw_response)}")
    except Exception as e:
        print(f"Error in get_sound_list: {e}")

    # 2. Try to get categories if possible via private method (RISKY but needed for investigation)
    # Common commands: "GetSoundlist", "GetCategories", "GetCategoryList"
    try:
        # access private method for testing
        if hasattr(client.remote, '_send_request'):
             # Try native commands
             resp = client.remote._send_request("GetCategories")
             print(f"GetCategories response: {repr(resp)}")
             
             resp2 = client.remote._send_request("GetCategoryList")
             print(f"GetCategoryList response: {repr(resp2)}")
    except Exception as e:
        print(f"Error probing private methods: {e}")
        
else:
    print("Could not connect to Soundpad.")
