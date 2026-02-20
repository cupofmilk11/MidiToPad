
import logging
import xml.etree.ElementTree as ET
from soundpad_control import SoundpadRemoteControl
from soundpad_control.remote_control import PlayStatus

class SoundpadClient:
    def __init__(self):
        self.remote = SoundpadRemoteControl()
        # FIX: Increase chunk size to handle large XML responses (default 1024 is too small)
        self.remote.chuck_size = 1024 * 1024 * 10 # 10MB
        self.connected = False
        self.current_sound_index = 1
        self.max_sound_index = 0
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Attempts to connect to Soundpad."""
        try:
            # Check if Soundpad is alive
            if self.remote.is_alive():
                self.connected = True
                self.logger.info("Connected to Soundpad.")
                return True
            else:
                self.connected = False
                self.logger.warning("Soundpad is not running or not reachable.")
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to Soundpad: {e}")
            self.connected = False
            return False

    def get_sound_list(self):
        """Retrieves and parses the sound list from Soundpad."""
        if not self.connected:
            if not self.connect():
                return []

        try:
            # Based on API, get_sound_list likely returns XML string or response object
            response = self.remote.get_sound_list()
            
            # If response is None or empty
            if not response:
                return []

            # If it's bytes, decode
            if isinstance(response, bytes):
                response = response.decode('utf-8')

            # Parse XML
            # Expected format: <Soundlist><Sound index="1" title="Sound1" ... /></Soundlist>
            # OR <Soundlist><Sound id="1" title="..." .../></Soundlist>
            
            # Check if response is already a list (if lib parses it)
            if isinstance(response, list):
                self.max_sound_index = len(response)
                return response

            root = ET.fromstring(response)
            sounds = []
            for sound in root.findall('Sound'):
                # Attributes might vary, usually 'index' and 'title'
                idx = sound.get('index')
                title = sound.get('title')
                if idx and title:
                    sounds.append({'index': int(idx), 'title': title})
            
            self.max_sound_index = len(sounds)
            return sounds

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse Soundpad XML: {e}")
            # Try to log raw response for debug
            self.logger.debug(f"Raw response: {response}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting sound list: {e}")
            return []

    def play_sound(self, index, speakers=True, mic=True):
        """Plays a sound by its index."""
        if not self.connected:
            return
        
        try:
            # Note: play_sound might be a wrapper in soundpad_control, 
            # but usually it calls DoPlaySound
            if hasattr(self.remote, 'play_sound'):
                self.remote.play_sound(index, speakers=speakers, mic=mic)
            else:
                 # Fallback if library differs
                 self.remote.DoPlaySound(index, speakers, mic)
        except Exception as e:
            self.logger.error(f"Error playing sound {index}: {e}")

    def select_sound(self, index):
        """Selects a sound in the Soundpad UI by its index."""
        if not self.connected:
            return
            
        try:
            if hasattr(self.remote, 'select_sound'):
                self.remote.select_sound(index)
            else:
                 # Fallback if library differs
                 self.remote.DoSelectSound(index)
        except Exception as e:
            self.logger.error(f"Error selecting sound {index}: {e}")

    def get_playback_status(self):
        """Returns the current playback status."""
        if self.connected:
            try:
                # Try standard command if available in wrapper
                if hasattr(self.remote, 'get_playback_status'):
                    return self.remote.get_playback_status()
                
                # Else try to send raw request
                # This depends on soundpad_control implementation of _send_request or similar
                # Looking at viewed code, it imports SoundpadRemoteControl.
                # If that class has _send_request or send_command...
                # We saw in previous turns: client.remote._send_request("GetCategories")
                
                if hasattr(self.remote, '_send_request'):
                    return self.remote._send_request("GetPlayStatus")
                    
            except Exception as e:
                self.logger.error(f"Error getting playback status: {e}")
        return None

    def stop_playback(self):
        if not self.connected:
            return
        try:
            self.remote.stop_sound()
        except Exception as e:
            self.logger.error(f"Error stopping playback: {e}")

    def toggle_pause(self):
        if not self.connected:
            return
        try:
            self.remote.toggle_pause()
        except Exception as e:
            self.logger.error(f"Error toggling pause: {e}")

    def play_pause_selected(self):
        """Smartly plays the selected sound if stopped, or toggles pause if playing."""
        if not self.connected:
            return
        try:
            status = self.remote.get_play_status()
            if status == PlayStatus.STOPPED:
                self.remote.play_selected_sound()
            else:
                self.remote.toggle_pause()
        except Exception as e:
            self.logger.error(f"Error handling play/pause: {e}")

    def select_next(self):
        """Selects the next sound in the list without playing it using internal index."""
        if not self.connected or self.max_sound_index == 0:
            return
        try:
            if self.current_sound_index < self.max_sound_index:
                self.current_sound_index += 1
            self.remote.select_row(self.current_sound_index)
        except Exception as e:
            self.logger.error(f"Error selecting next sound: {e}")

    def select_previous(self):
        """Selects the previous sound in the list without playing it using internal index."""
        if not self.connected or self.max_sound_index == 0:
            return
        try:
            if self.current_sound_index > 1:
                self.current_sound_index -= 1
            self.remote.select_row(self.current_sound_index)
        except Exception as e:
            self.logger.error(f"Error selecting previous sound: {e}")

    def select_next_category(self):
        """Selects the next category in Soundpad."""
        if not self.connected:
            return
        try:
            self.remote.select_next_category()
        except Exception as e:
            self.logger.error(f"Error selecting next category: {e}")

    def select_previous_category(self):
        """Selects the previous category in Soundpad."""
        if not self.connected:
            return
        try:
            self.remote.select_previous_category()
        except Exception as e:
            self.logger.error(f"Error selecting previous category: {e}")
