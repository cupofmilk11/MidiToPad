
import json
import os
import logging
def get_appdata_dir():
    appdata = os.getenv('APPDATA')
    if appdata:
        path = os.path.join(appdata, "MidiToPad")
    else:
        path = os.getcwd()
    os.makedirs(path, exist_ok=True)
    return path

appdata_dir = get_appdata_dir()
CONFIG_FILE = os.path.join(appdata_dir, "config.json")

# Migrate old config if it exists
old_config = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "config.json")
if os.path.exists(old_config) and not os.path.exists(CONFIG_FILE):
    import shutil
    try:
        shutil.copy2(old_config, CONFIG_FILE)
    except Exception:
        pass

class ConfigManager:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        default_soundpad_folder = os.path.join(os.getenv('APPDATA'), "Leppsoft")
        # Check if actually exists, if not leave empty
        if not os.path.exists(default_soundpad_folder):
             default_soundpad_folder = ""

        self.config = {
            "midi_device": "",
            "soundpad_data_folder": default_soundpad_folder,
            "soundpad_exe_path": "",
            "auto_start_soundpad": False,
            "soundpad_via_steam": False,
            "mappings": {},  # Format: "note_number": {"sound_index": 1, "sound_title": "Sound Name"}
            "global_hotkeys": {}, # Format: "action_name": note_number (int)
            "custom_macros": {} # Format: "note_number_string": "keyboard_shortcut"
        }
        self.load_config()

    def load_config(self):
        """Loads configuration from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Update default config with loaded values to ensure structure
                    self.config.update(loaded_config)
                    
                    # PURGE OBSOLETE KEYS (Feature removed)
                    needs_save = False
                    if "global_hotkeys" in self.config:
                        for k in ["next", "prev"]:
                            if k in self.config["global_hotkeys"]:
                                self.config["global_hotkeys"].pop(k, None)
                                needs_save = True
                    
                                
                self.logger.info("Configuration loaded.")
                if needs_save:
                    self.save_config()
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")
        else:
            self.logger.info("No config file found, using defaults.")

    def save_config(self):
        """Saves current configuration to JSON file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.logger.info("Configuration saved.")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def get_midi_device(self):
        return self.config.get("midi_device", "")

    def set_midi_device(self, device_name):
        self.config["midi_device"] = device_name
        self.save_config()

    def get_soundpad_data_folder(self):
        return self.config.get("soundpad_data_folder", "")

    def set_soundpad_data_folder(self, path):
        self.config["soundpad_data_folder"] = path
        self.save_config()

    def get_soundpad_exe_path(self):
        return self.config.get("soundpad_exe_path", "")

    def set_soundpad_exe_path(self, path):
        self.config["soundpad_exe_path"] = path
        self.save_config()

    def get_auto_start_soundpad(self):
        return self.config.get("auto_start_soundpad", False)

    def set_auto_start_soundpad(self, value):
        self.config["auto_start_soundpad"] = bool(value)
        self.save_config()

    def get_soundpad_via_steam(self):
        return self.config.get("soundpad_via_steam", False)

    def set_soundpad_via_steam(self, value):
        self.config["soundpad_via_steam"] = bool(value)
        self.save_config()

    def _clear_conflicting_bindings(self, note):
        """Removes the given note from all other bindings to guarantee exclusivity."""
        note_str = str(note)
        
        # 1. Clear from mappings
        if "mappings" in self.config and note_str in self.config["mappings"]:
            del self.config["mappings"][note_str]
            
        # 2. Clear from global_hotkeys
        if "global_hotkeys" in self.config:
            to_remove = []
            for action, h_note in self.config["global_hotkeys"].items():
                if str(h_note) == note_str:
                    to_remove.append(action)
            for action in to_remove:
                del self.config["global_hotkeys"][action]
                
        # 3. Clear from custom macros
        if "custom_macros" in self.config and note_str in self.config["custom_macros"]:
            del self.config["custom_macros"][note_str]

    def get_mapping(self, note):
        """Returns mapping for a given note number.
        Returns None or dict {'sound_index': int, 'sound_title': str}
        """
        # JSON keys are strings, so cast note to str
        return self.config["mappings"].get(str(note))

    def set_mapping(self, note, sound_index, sound_title, custom_label=None, custom_color=None):
        """Sets a mapping for a note."""
        # Preserve existing custom values if not provided
        current = self.config["mappings"].get(str(note), {})
        
        self._clear_conflicting_bindings(note)
        
        mapping = {
            "sound_index": sound_index,
            "sound_title": sound_title,
            "custom_label": custom_label if custom_label is not None else current.get("custom_label"),
            "custom_color": custom_color if custom_color is not None else current.get("custom_color")
        }
        self.config["mappings"][str(note)] = mapping
        self.save_config()

    def set_custom_label(self, note, label):
        """Updates only the custom label."""
        if str(note) in self.config["mappings"]:
            self.config["mappings"][str(note)]["custom_label"] = label
            self.save_config()

    def set_custom_color(self, note, color):
        """Updates only the custom color."""
        if str(note) in self.config["mappings"]:
            self.config["mappings"][str(note)]["custom_color"] = color
            self.save_config()

    def remove_mapping(self, note):
        """Removes a mapping for a note."""
        if str(note) in self.config["mappings"]:
            del self.config["mappings"][str(note)]
            self.save_config()

    def get_global_hotkeys(self):
        """Returns the dictionary of global hotkeys {action: note_number}."""
        return self.config.get("global_hotkeys", {})

    def set_global_hotkey(self, action, note):
        """Sets a MIDI note as a global hotkey for a specific action."""
        if "global_hotkeys" not in self.config:
            self.config["global_hotkeys"] = {}
            
        self._clear_conflicting_bindings(note)
        
        try:
            self.config["global_hotkeys"][action] = int(note)
        except ValueError:
            self.config["global_hotkeys"][action] = str(note)
        self.save_config()

    def remove_global_hotkey(self, action):
        """Removes a global hotkey assignment."""
        if "global_hotkeys" in self.config and action in self.config["global_hotkeys"]:
            del self.config["global_hotkeys"][action]
            self.save_config()

    def get_custom_macros(self):
        """Returns the dictionary of custom macros {note_number: keyboard_shortcut}."""
        return self.config.get("custom_macros", {})

    def set_custom_macro(self, note, shortcut):
        """Sets a MIDI note as a custom macro shortcut."""
        if "custom_macros" not in self.config:
            self.config["custom_macros"] = {}
            
        self._clear_conflicting_bindings(note)
        
        self.config["custom_macros"][str(note)] = shortcut
        self.save_config()

    def remove_custom_macro(self, note):
        """Removes a custom macro assignment."""
        if "custom_macros" in self.config and str(note) in self.config["custom_macros"]:
            del self.config["custom_macros"][str(note)]
            self.save_config()
