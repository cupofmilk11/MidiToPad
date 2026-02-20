
import customtkinter as ctk
import logging
import threading
import tkinter as tk
import subprocess
import time
import os
import sys
import keyboard
from src.soundpad.client import SoundpadClient
from src.midi.manager import MidiManager
from src.config.settings import ConfigManager
from src.gui.visual_keyboard import VisualKeyboard
from src.gui.settings_window import SettingsWindow
from src.gui.library_frame import LibraryFrame

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.MAX_PIANO_HEIGHT = 533 # Ограничение высоты пианино при растягивании окна
        self.visual_keyboards = [] # Список всех активных клавиатур для сихнронизации

        # --- Managers ---
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.soundpad_client = SoundpadClient()
        self.midi_manager = MidiManager()
        self.available_sounds = [] # List of dicts {index, title}
        self.assigning_note = None # Tracks the note waiting for a sound

        # --- Window Config ---
        self.title("MidiToPad")
        self.geometry("1200x400") # Wider for keyboard
        self.minsize(800, 300)

        # Set window icon
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # --- Grid Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar (Left) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MidiToPad", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(15, 5))

        # MIDI Selection
        self.midi_label = ctk.CTkLabel(self.sidebar_frame, text="MIDI Device:", anchor="w")
        self.midi_label.grid(row=1, column=0, padx=20, pady=(5, 0))
        
        self.midi_option_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["No Device"], command=self.change_midi_device)
        self.midi_option_menu.grid(row=2, column=0, padx=20, pady=(5, 5))

        self.refresh_btn = ctk.CTkButton(self.sidebar_frame, text="Refresh Devices", command=self.refresh_midi_devices)
        self.refresh_btn.grid(row=3, column=0, padx=20, pady=(0, 5))

        # Connect Button
        self.connect_btn = ctk.CTkButton(self.sidebar_frame, text="Reconnect Soundpad", command=self.connect_soundpad)
        self.connect_btn.grid(row=4, column=0, padx=20, pady=(0, 10))
        
        # Always on Top Switch
        self.always_on_top_var = ctk.BooleanVar(value=False)
        self.always_on_top_switch = ctk.CTkSwitch(self.sidebar_frame, text="Over all", 
                                                  variable=self.always_on_top_var,
                                                  command=self.toggle_always_on_top)
        self.always_on_top_switch.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="s")
        
        # Pop-out Piano Button
        self.popout_btn = ctk.CTkButton(self.sidebar_frame, text="🎹 fix keyboard", command=self.open_popout_piano)
        self.popout_btn.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="s")

        # Hold to Play Switch
        self.hold_to_play_var = ctk.BooleanVar(value=False)
        self.hold_to_play_switch = ctk.CTkSwitch(self.sidebar_frame, text="To Hold", 
                                                 variable=self.hold_to_play_var)
        self.hold_to_play_switch.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="s")

        # Settings Button
        self.settings_btn = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.open_settings)
        self.settings_btn.grid(row=8, column=0, padx=20, pady=10, sticky="s")

        # --- Main Area (Right) ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=0) # Keyboard row (fixed height)
        self.main_frame.grid_rowconfigure(2, weight=1) # Library row (expands)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Keyboard Area
        self.kbd_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.kbd_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15)) # Отступ снизу для защиты от обрезания (pady)
        self.kbd_frame.grid_columnconfigure(1, weight=1) # The keyboard expands horizontally
        self.kbd_frame.grid_rowconfigure(0, weight=1)    # The keyboard and buttons expand vertically
        
        # Shift Left Button
        self.shift_left_btn = ctk.CTkButton(self.kbd_frame, text="◀", width=30,
                                            command=lambda: self.shift_all_octaves(-1))
        self.shift_left_btn.grid(row=0, column=0, padx=(0, 5), sticky="ns")

        # Init with 2 octaves, starting at C4
        # Высота пианино настраивается параметром MAX_PIANO_HEIGHT
        self.keyboard = VisualKeyboard(self.kbd_frame, start_octave=4, num_octaves=2, height=self.MAX_PIANO_HEIGHT, max_height_limit=self.MAX_PIANO_HEIGHT)
        self.keyboard.grid(row=0, column=1, sticky="nsew") # sticky="nsew" чтобы всё растягивалось равномерно
        self.keyboard.on_key_context = self.show_context_menu
        self.keyboard.on_key_click = self.on_key_click
        self.visual_keyboards.append(self.keyboard)
        
        # Shift Right Button
        self.shift_right_btn = ctk.CTkButton(self.kbd_frame, text="▶", width=30,
                                             command=lambda: self.shift_all_octaves(1))
        self.shift_right_btn.grid(row=0, column=2, padx=(5, 0), sticky="ns")

        # Library
        self.library = LibraryFrame(self.main_frame, self.config_manager, 
                                    on_sound_selected=self.on_library_sound_selected,
                                    on_play_sound=self.on_library_play_sound,
                                    on_bind_playing=self.on_library_bind_playing_request,
                                    on_select_soundpad=self.on_library_select_soundpad,
                                    on_api_sync_request=self.sync_library_from_api)
        self.library.grid(row=2, column=0, sticky="nsew")

        # Status Label (Moved to Library Header)
        self.status_label = ctk.CTkLabel(self.library.sound_header, text="Soundpad: Disconnected", text_color="gray")
        self.status_label.pack(side="left", padx=10, fill="x", expand=True)

        # --- Logic Binding ---
        self.midi_manager.set_callback(self.on_midi_message)

        # --- Initialization ---
        self.after(100, self.init_backend)

    def init_backend(self):
        """Initializes backend services asynchronously."""
        self.connect_soundpad()
        
        devices = self.midi_manager.get_input_devices()
        if devices:
            self.midi_option_menu.configure(values=devices)
            saved_device = self.config_manager.get_midi_device()
            if saved_device in devices:
                self.midi_option_menu.set(saved_device)
                self.midi_manager.open_port(saved_device)
            else:
                 self.midi_option_menu.set(devices[0])
                 # self.change_midi_device(devices[0]) # Auto-connect?
        else:
            self.midi_option_menu.configure(values=["No Devices Found"])
            self.midi_option_menu.set("No Devices Found")

        # Load mappings to GUI
        self.refresh_mappings()
        
        # Proactively refresh sounds list to avoid empty errors
        self.connect_soundpad()

    def connect_soundpad(self):
        def _connect():
            connected = self.soundpad_client.connect()
            
            # Auto-start logic
            if not connected and self.config_manager.get_auto_start_soundpad():
                if self.config_manager.get_soundpad_via_steam():
                    self.logger.info("Attempting to auto-start Soundpad via Steam (steam://rungameid/629520)")
                    try:
                        os.startfile("steam://rungameid/629520")
                        time.sleep(5)
                        connected = self.soundpad_client.connect()
                    except Exception as e:
                        self.logger.error(f"Failed to auto-start Soundpad via Steam: {e}")
                else:
                    exe_path = self.config_manager.get_soundpad_exe_path()
                    if exe_path and os.path.exists(exe_path):
                        self.logger.info(f"Attempting to auto-start Soundpad from: {exe_path}")
                        try:
                            # os.startfile is more reliable for starting Windows GUI apps than subprocess.Popen
                            os.startfile(exe_path)
                            # Wait a bit longer for it to spin up API
                            time.sleep(5)
                            connected = self.soundpad_client.connect()
                        except Exception as e:
                            self.logger.error(f"Failed to auto-start Soundpad: {e}")

            if connected:
                self.available_sounds = self.soundpad_client.get_sound_list()
                
                def _update_ui():
                    count = len(self.available_sounds)
                    if count > 0:
                        self.status_label.configure(text=f"Soundpad: Connected ({count} sounds)", text_color="green")
                        self.logger.info(f"Loaded {count} sounds from Soundpad.")
                    else:
                        self.status_label.configure(text="Soundpad: Connected (0 sounds!)", text_color="orange")
                        self.logger.warning("Soundpad connected but returned 0 sounds. Check Soundpad configuration or restart it.")
                self.after(0, _update_ui)
            else:
                def _update_ui_fail():
                    self.status_label.configure(text="Soundpad: Disconnected", text_color="red")
                self.after(0, _update_ui_fail)
        
        threading.Thread(target=_connect, daemon=True).start()

    def change_midi_device(self, new_device):
        if new_device and new_device not in ["No Devices Found", "No Device"]:
            self.midi_manager.open_port(new_device)
            self.config_manager.set_midi_device(new_device)

    def refresh_midi_devices(self):
        """Refreshes the list of available MIDI devices."""
        devices = self.midi_manager.get_input_devices()
        if devices:
            self.midi_option_menu.configure(values=devices)
            current = self.midi_option_menu.get()
            if current == "No Devices Found" or current == "No Device":
                self.midi_option_menu.set(devices[0])
                self.change_midi_device(devices[0])
            elif current not in devices:
                self.midi_option_menu.set(devices[0])
                self.change_midi_device(devices[0])
        else:
            self.midi_option_menu.configure(values=["No Devices Found"])
            self.midi_option_menu.set("No Devices Found")

    def on_midi_message(self, note, velocity, is_note_on=True):
        """Called when a MIDI note ON or OFF event is received."""
        
        # If Hold to Play is OFF, we completely ignore note_off events
        if not is_note_on and not self.hold_to_play_var.get():
            return

        # 1. Check if we're assigning a global hotkey in SettingsWindow
        assigning_action = getattr(self, 'assigning_global_hotkey', None)
        if assigning_action:
            if not is_note_on:
                return # Ignore release for assignment
            for child in self.winfo_children():
                if isinstance(child, ctk.CTkToplevel) and hasattr(child, 'on_hotkey_received'):
                    # Call the callback in the main thread
                    self.after(0, lambda c=child, a=assigning_action, n=note: c.on_hotkey_received(a, n))
                    break
            return

        # 2. Check if the note is a global hotkey for Soundpad
        global_hotkeys = self.config_manager.get_global_hotkeys()
        for action, hotkey_note in global_hotkeys.items():
            if note == hotkey_note:
                if not is_note_on:
                    return # Ignore release for global hotkeys
                if action == "play_pause":
                    threading.Thread(target=self.soundpad_client.play_pause_selected, daemon=True).start()
                elif action == "next_category":
                    threading.Thread(target=self.soundpad_client.select_next_category, daemon=True).start()
                elif action == "prev_category":
                    threading.Thread(target=self.soundpad_client.select_previous_category, daemon=True).start()
                elif action == "stop":
                    threading.Thread(target=self.soundpad_client.stop_playback, daemon=True).start()
                elif action == "toggle_hold":
                    self.after(0, lambda: self.hold_to_play_var.set(not self.hold_to_play_var.get()))
                
                # Visual feedback for global hotkeys on the keyboard
                def _flash_hotkey():
                    # Only flash if it's an integer note (piano key)
                    if isinstance(note, int):
                        for kb in self.visual_keyboards:
                            kb.highlight_key(note, on=True)
                        self.after(200, lambda: [kb.highlight_key(note, on=False) for kb in self.visual_keyboards])
                self.after(0, _flash_hotkey)
                    
                return # Skip playing assigned piano sounds

        # 2.5 Check if the note is a custom keyboard macro
        custom_macros = self.config_manager.get_custom_macros()
        for note_str, shortcut in custom_macros.items():
            if str(note) == note_str:
                if not is_note_on:
                    return # Ignore release
                
                # Execute the shortcut
                try:
                    threading.Thread(target=lambda s=shortcut: keyboard.send(s), daemon=True).start()
                except Exception as e:
                    logging.error(f"Failed to execute macro '{shortcut}': {e}")
                
                # Visual feedback
                def _flash_macro():
                    if isinstance(note, int):
                        for kb in self.visual_keyboards:
                            kb.highlight_key(note, on=True)
                        self.after(200, lambda: [kb.highlight_key(note, on=False) for kb in self.visual_keyboards])
                self.after(0, _flash_macro)
                
                return # Skip playing assigned piano sounds

        # 3. Stop if non-integer note (like CC events) reaches here and isn't a hotkey
        if not isinstance(note, int):
            return

        # Update UI in main thread (Standard Note Processing)
        def _ui_update():
            if not is_note_on:
                # Turn off highlight
                for kb in self.visual_keyboards:
                    kb.highlight_key(note, on=False)
                # Stop playback if it was mapped and hold-to-play is active
                mapping = self.config_manager.get_mapping(note)
                if mapping:
                    threading.Thread(target=self.soundpad_client.stop_playback, daemon=True).start()
                return

            # --- Note ON Logic ---
            
            # 1. Quick Bind in Edit Mode
            if hasattr(self, 'library') and self.library.is_edit_mode:
                if self.library.selected_sound:
                    sound = self.library.selected_sound
                    sound_idx = sound.get('api_index') or sound.get('index')
                    if sound_idx:
                        self.config_manager.set_mapping(note, int(sound_idx), sound['title'])
                        self.refresh_mappings()
                        
                        # Flash green feedback
                        for kb in self.visual_keyboards:
                            kb.highlight_key(note, on=True)
                        self.after(300, lambda: [kb.highlight_key(note, on=False) for kb in self.visual_keyboards])
                        self.logger.info(f"Quick bound Note {note} to {sound['title']}")
                        return # Stop processing, we just bound it

            # --- Standard playback and Auto-shift logic ---
            note_octave = note // 12
            start = self.keyboard.start_octave
            
            should_refresh = False
            
            if note_octave < start:
                # Key is to the left. Move start to this octave.
                for kb in self.visual_keyboards: kb.set_start_octave(note_octave)
                should_refresh = True
            elif note_octave > start + 1:
                # Key is to the right (beyond 2nd visible octave). 
                # Move start so this octave is the second one (i.e. start = note_oct - 1)
                for kb in self.visual_keyboards: kb.set_start_octave(note_octave - 1)
                should_refresh = True
            
            if should_refresh:
                self.refresh_mappings()

            # Highlight key
            for kb in self.visual_keyboards:
                kb.highlight_key(note, on=True)
                
            # Schedule turn off ONLY if Hold to Play is OFF
            if not self.hold_to_play_var.get():
                self.after(200, lambda: [kb.highlight_key(note, on=False) for kb in self.visual_keyboards])
            
            # Check mapping and play
            mapping = self.config_manager.get_mapping(note)
            if mapping:
                sound_index = mapping['sound_index']
                self.logger.info(f"Playing sound index {sound_index} for note {note}")
                # Run in separate thread to not block UI if play_sound blocks (it shouldn't)
                threading.Thread(target=self.soundpad_client.play_sound, args=(sound_index,), daemon=True).start()
        
        self.after(0, _ui_update)

    def open_popout_piano(self):
        """Creates a standalone, always-on-top window with a copy of the piano."""
        popout = ctk.CTkToplevel(self)
        popout.title("MidiToPad - Клавиатура")
        popout.geometry("800x200")
        popout.attributes("-topmost", True)
        
        kbd_frame = ctk.CTkFrame(popout, fg_color="transparent")
        kbd_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left Shift
        left_btn = ctk.CTkButton(kbd_frame, text="◀", width=30,
                                 command=lambda: self.shift_all_octaves(-1))
        left_btn.pack(side="left", fill="y", padx=(0, 5))
        
        # Piano
        new_kb = VisualKeyboard(kbd_frame, start_octave=self.keyboard.start_octave, 
                                num_octaves=2, height=200, max_height_limit=1000)
        new_kb.pack(side="left", fill="both", expand=True)
        new_kb.on_key_context = self.show_context_menu
        new_kb.on_key_click = self.on_key_click
        
        # Right Shift
        right_btn = ctk.CTkButton(kbd_frame, text="▶", width=30,
                                  command=lambda: self.shift_all_octaves(1))
        right_btn.pack(side="right", fill="y", padx=(5, 0))
        
        self.visual_keyboards.append(new_kb)
        
        # Refresh its mappings right away
        self.refresh_mappings()
        
        # Cleanup when closed
        def on_close():
            self.visual_keyboards.remove(new_kb)
            popout.destroy()
            
        popout.protocol("WM_DELETE_WINDOW", on_close)

    def shift_all_octaves(self, delta):
        """Helper to shift all open keyboards at once."""
        new_start = self.keyboard.start_octave + delta
        # VisualKeyboard clamps internally, but we want all synced
        for kb in self.visual_keyboards:
            kb.set_start_octave(new_start)

    def open_settings(self):
        SettingsWindow(self, self.config_manager, on_close_callback=self.library.refresh)

    def on_library_sound_selected(self, sound):
        # If we are in assignment mode, assign directly and exit mode
        if getattr(self, 'assigning_note', None) is not None:
            note = self.assigning_note
            self.assigning_note = None # Reset
            
            # Need to find matching API sound index
            api_sound = self._find_sound_in_api(sound['title'])
            if api_sound:
                self.assign_sound(note, api_sound)
                self.status_label.configure(text=f"Assigned '{sound['title']}' to {note}", text_color="green")
            else:
                self.status_label.configure(text="Error: Sound not synced with Soundpad list", text_color="red")
            
            # Remove highlight hint
            for kb in self.visual_keyboards:
                kb.highlight_key(note, on=False)
            return

        self.logger.info(f"Selected sound from library: {sound['title']}")
        self.status_label.configure(text=f"Selected: {sound['title']}", text_color="blue")
        self.current_selected_sound = sound

    def _find_sound_in_api(self, target_title):
        """Helper to match a library sound title to the loaded api sounds."""
        lib_title = target_title.strip().lower()
        for api_sound in getattr(self, 'available_sounds', []):
            if api_sound['title'].strip().lower() == lib_title:
                return api_sound
        return None

    def on_library_play_sound(self, sound_index):
        """Plays sound directly from library."""
        self.logger.info(f"Double-click playing sound index: {sound_index}")
        threading.Thread(target=self.soundpad_client.play_sound, args=(sound_index,), daemon=True).start()

    def on_library_bind_playing_request(self, sound):
        """Called when user right-clicks a sound and wants to bind it to a key."""
        self.assigning_sound_from_library = sound
        self.status_label.configure(text=f"Waiting: Click any key above to bind '{sound['title']}'", text_color="orange")

    def on_library_select_soundpad(self, sound_index):
        """Called when user wants to select a sound in the Soundpad UI."""
        # Need to implement select_sound in client. Assume we just play it if we can't select?
        # Let's add select_sound to client if absent, or just try.
        if hasattr(self.soundpad_client, 'select_sound'):
            threading.Thread(target=self.soundpad_client.select_sound, args=(sound_index,), daemon=True).start()
        else:
            self.logger.warning("select_sound not implemented in soundpad client")

    def refresh_mappings(self):
        """Updates keyboard labels based on config."""
        # Clear all first (optional, but good if keys moved)
        # Actually VisualKeyboard doesn't have clear_all_labels, but we can redraw or just overwrite.
        
        mappings = self.config_manager.config["mappings"]
        for note_str, data in mappings.items():
            note = int(note_str)
            # Label: Use custom if exists, else title
            label = data.get('custom_label') or data.get('sound_title')
            # Color: Use custom if exists
            color = data.get('custom_color')
            
            for kb in self.visual_keyboards:
                kb.set_key_label(note, label)
                kb.set_key_color(note, color)
        # Redraw to ensure everything is applied if needed, though set_key methods do it
        # self.keyboard.draw_keyboard()

    def show_context_menu(self, note, event):
        """Shows context menu for assigning sounds."""
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", 
                       activebackground="#1f538d", activeforeground="white", 
                       relief="flat", borderwidth=0)
        
        # Mapping Info
        mapping = self.config_manager.get_mapping(note)
        if mapping:
            title = mapping.get('custom_label') or mapping['sound_title']
            menu.add_command(label=f"Note {note}: {title}", state="disabled")
            menu.add_separator()
            
            # Additional Actions
            menu.add_command(label="▶ Play Sound", command=lambda: self.play_mapped_sound(note))
            menu.add_command(label="✖ Clear Key (Reset)", command=lambda: self.unassign_sound(note))
            menu.add_separator()
        
        # Customization
        menu.add_command(label="✎ Rename Key", command=lambda: self.rename_key_dialog(note))
        menu.add_command(label="🎨 Set Color", command=lambda: self.color_key_dialog(note))
        menu.add_separator()
        
        # Assign Sound
        menu.add_command(label="➕ Assign Sound...", command=lambda: self.enter_assign_mode(note))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def enter_assign_mode(self, note):
        self.assigning_note = note
        self.status_label.configure(text=f"Waiting: Select a sound for Note {note} in the list below", text_color="orange")
        # Visual hint on the key
        for kb in self.visual_keyboards:
            kb.highlight_key(note, on=True)

    def play_mapped_sound(self, note):
        mapping = self.config_manager.get_mapping(note)
        if mapping:
            sound_index = mapping['sound_index']
            threading.Thread(target=self.soundpad_client.play_sound, args=(sound_index,), daemon=True).start()
            for kb in self.visual_keyboards:
                kb.highlight_key(note, on=True)
            self.after(200, lambda: [kb.highlight_key(note, on=False) for kb in self.visual_keyboards])

    def on_key_click(self, note):
        # 1. Check if we are binding a sound from the library (Right-click "Bind" in Library)
        if getattr(self, 'assigning_sound_from_library', None) is not None:
            sound = self.assigning_sound_from_library
            # Match API index
            api_sound = self._find_sound_in_api(sound['title'])
            if api_sound:
                self.assign_sound(note, api_sound)
                self.status_label.configure(text=f"Assigned '{sound['title']}' to {note}", text_color="green")
            else:
                self.status_label.configure(text="Error: Sound not synced with Soundpad list", text_color="red")
            
            # Reset
            self.assigning_sound_from_library = None
            return

        # 2. Check Edit Mode
        if self.library.is_edit_mode:
            # If edit mode is on, left click traditionally selected a sound from the list to assign it.
            if hasattr(self, 'current_selected_sound') and self.current_selected_sound:
                sound = self.current_selected_sound
                # Match by title or index
                matched = False
                self.logger.info(f"Trying to match library sound '{sound['title']}' against {len(self.available_sounds)} API sounds.")
                
                # Check api_index directly if available
                if 'api_index' in sound:
                    for api_sound in getattr(self, 'available_sounds', []):
                        if api_sound.get('index') == sound['api_index']:
                            self.assign_sound(note, api_sound)
                            matched = True
                            break
                
                # Fallback to title match
                if not matched:
                    lib_title = sound['title'].strip().lower()
                    for api_sound in getattr(self, 'available_sounds', []):
                        if api_sound['title'].strip().lower() == lib_title:
                            self.assign_sound(note, api_sound)
                            matched = True
                            break
                
                if matched:
                    self.status_label.configure(text=f"Assigned {sound['title']} to {note}", text_color="green")
                else:
                    msg = "Sound not found in active Soundpad list!"
                    if len(self.available_sounds) == 0:
                        msg += " (List is empty)"
                    self.status_label.configure(text=msg, text_color="orange")
            return

        # 3. Normal Mode: Play the sound!
        mapping = self.config_manager.get_mapping(note)
        if mapping:
            # Visual feedback is handled in play_mapped_sound
            self.play_mapped_sound(note)


    def assign_sound(self, note, sound):
        self.config_manager.set_mapping(note, sound['index'], sound['title'])
        # Refresh to apply label/color if they existed or update title
        self.refresh_mappings()

    def unassign_sound(self, note):
        self.config_manager.remove_mapping(note)
        for kb in self.visual_keyboards:
            kb.set_key_label(note, "")
            kb.set_key_color(note, None) # Reset color too? Or keep?
        # Probably reset color if map removed? Or allow coloring empty keys? 
        # User said "customize key", likely implies mapped key or any key.
        # If we allow coloring any key, we must store it in config even if no sound.
        # Current config structure links mapping to note.
        # If we want to color empty keys, we need to adapt set_mapping logic to allow None sound.
        # For now, let's assume coloring works primarily on keys. 
        # If user wants to color specific key, we should let them.
        # So we shouldn't delete mapping entirely if only sound is gone but color remains?
        # Simple approach: unassign removes sound but maybe keeps color? 
        # delete config["mappings"][str(note)] removes EVERYTHING.
        # So unassign clears everything.

    def rename_key_dialog(self, note):
        dialog = ctk.CTkInputDialog(text=f"Rename key {note}:", title="Rename Key")
        new_name = dialog.get_input()
        if new_name is not None:
            # We need to ensure a mapping entry exists to save this.
            # If no sound mapped, we create a dummy mapping? 
            # Or just check if mapping exists.
            mapping = self.config_manager.get_mapping(note)
            if not mapping:
                # If valid use case to name empty key, we need to support it.
                # Create empty mapping
                self.config_manager.set_mapping(note, -1, "", custom_label=new_name)
            else:
                 self.config_manager.set_custom_label(note, new_name)
            
            self.refresh_mappings()

    def color_key_dialog(self, note, event=None):
        # Use a simple color chooser or preset list. 
        # CTk doesn't have built-in color picker. Tkinter has askcolor.
        from tkinter.colorchooser import askcolor
        color = askcolor(title="Choose Key Color")
        if color[1]: # color is ((r,g,b), hex)
            hex_color = color[1]
            
            mapping = self.config_manager.get_mapping(note)
            if not mapping:
                self.config_manager.set_mapping(note, -1, "", custom_color=hex_color)
            else:
                self.config_manager.set_custom_color(note, hex_color)
            
            self.refresh_mappings()

    def open_assign_dialog(self, note):
        """Opens a top level window to select a sound."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Assign Sound to Note {note}")
        dialog.geometry("400x500")
        
        # Search Entry
        search_var = ctk.StringVar()
        entry = ctk.CTkEntry(dialog, placeholder_text="Search...", textvariable=search_var)
        entry.pack(padx=10, pady=10, fill="x")
        
        # Scrollable Frame with buttons
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        def filter_sounds(*args):
             # Clear current buttons
            for widget in scroll.winfo_children():
                widget.destroy()
            
            query = search_var.get().lower()
            count = 0
            for sound in self.available_sounds:
                if query in sound['title'].lower():
                    btn = ctk.CTkButton(scroll, text=sound['title'], anchor="w",
                                        command=lambda s=sound: [self.assign_sound(note, s), dialog.destroy()])
                    btn.pack(fill="x", pady=2)
                    count += 1
                    if count > 50: # Limit display for performance
                        break

        entry.bind("<KeyRelease>", lambda e: filter_sounds())
        
        # Initial populate
        filter_sounds()

    def toggle_always_on_top(self):
        state = self.always_on_top_var.get()
        self.attributes("-topmost", state)

    def sync_library_from_api(self):
        """Fetches the flat sound list directly from Soundpad API and loads it into the library."""
        if hasattr(self, 'status_label'):
            self.status_label.configure(text="Syncing with Soundpad...", text_color="orange")
        self.update_idletasks()
        
        def _sync():
            if not self.soundpad_client.connected:
                self.soundpad_client.connect()
                
            if self.soundpad_client.connected:
                sounds = self.soundpad_client.get_sound_list()
                if sounds:
                    self.available_sounds = sounds
                    self.after(0, lambda: self.library.load_api_sounds(sounds))
                    if hasattr(self, 'status_label'):
                        self.after(0, lambda: self.status_label.configure(text=f"API Sync: Loaded {len(sounds)} sounds", text_color="green"))
                else:
                    if hasattr(self, 'status_label'):
                        self.after(0, lambda: self.status_label.configure(text="API Sync: 0 sounds found", text_color="red"))
            else:
                if hasattr(self, 'status_label'):
                    self.after(0, lambda: self.status_label.configure(text="Soundpad disconnected", text_color="red"))
                
        import threading
        threading.Thread(target=_sync, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
