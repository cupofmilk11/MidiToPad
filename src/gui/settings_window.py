
import customtkinter as ctk
from tkinter import filedialog
import webbrowser

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, config_manager, on_close_callback=None):
        super().__init__(master)
        self.config_manager = config_manager
        self.on_close_callback = on_close_callback
        
        self.title("Settings")
        self.geometry("550x650")
        self.resizable(False, False)
        
        # Make modal
        self.transient(master)
        self.grab_set()
        self.focus()
        
        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tabview.add("Soundpad")
        self.tabview.add("Macros")
        self.tabview.add("about dev")
        
        tab_sp = self.tabview.tab("Soundpad")
        tab_sp.grid_columnconfigure(1, weight=1)
        
        tab_mac = self.tabview.tab("Macros")
        tab_mac.grid_columnconfigure(0, weight=1)
        
        tab_about = self.tabview.tab("about dev")
        tab_about.grid_columnconfigure(0, weight=1)
        
        # --- Soundpad Tab ---
        # Soundpad Folder
        self.folder_label = ctk.CTkLabel(tab_sp, text="Soundpad Data Folder:")
        self.folder_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        self.folder_entry = ctk.CTkEntry(tab_sp, width=250)
        self.folder_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.folder_entry.insert(0, self.config_manager.get_soundpad_data_folder())
        
        self.browse_btn = ctk.CTkButton(tab_sp, text="Browse", width=60, command=self.browse_folder)
        self.browse_btn.grid(row=0, column=2, padx=(0, 20), pady=10)
        
        # Explanation
        self.info_label = ctk.CTkLabel(tab_sp, text="Select the folder where 'soundlist.spl' or exported spl files are located.\nThe app will scan for spl files in this folder.", 
                                       text_color="gray", font=ctk.CTkFont(size=12))
        self.info_label.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")
        
        # Soundpad Executable
        self.exe_label = ctk.CTkLabel(tab_sp, text="Soundpad Executable:")
        self.exe_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        self.exe_entry = ctk.CTkEntry(tab_sp, width=250)
        self.exe_entry.grid(row=2, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.exe_entry.insert(0, self.config_manager.get_soundpad_exe_path())
        
        self.browse_exe_btn = ctk.CTkButton(tab_sp, text="Browse", width=60, command=self.browse_exe)
        self.browse_exe_btn.grid(row=2, column=2, padx=(0, 20), pady=10)
        
        # Auto Start Checkbox
        self.auto_start_var = ctk.BooleanVar(value=self.config_manager.get_auto_start_soundpad())
        self.auto_start_cb = ctk.CTkCheckBox(tab_sp, text="Start Soundpad with application (if not running)", variable=self.auto_start_var)
        self.auto_start_cb.grid(row=3, column=0, columnspan=3, padx=20, pady=(10, 5), sticky="w")

        # Steam Start Checkbox
        self.steam_start_var = ctk.BooleanVar(value=self.config_manager.get_soundpad_via_steam())
        self.steam_start_cb = ctk.CTkCheckBox(tab_sp, text="Soundpad в Steam (запускает через steam://rungameid/629520)", variable=self.steam_start_var)
        self.steam_start_cb.grid(row=4, column=0, columnspan=3, padx=20, pady=(5, 10), sticky="w")
        
        # Global Hotkeys Section
        self.hotkeys_label = ctk.CTkLabel(tab_sp, text="Global MIDI Hotkeys", font=ctk.CTkFont(size=16, weight="bold"))
        self.hotkeys_label.grid(row=5, column=0, columnspan=3, pady=(20, 10))
        
        self.hotkey_actions = {
            "play_pause": "Воспроизведение / Пауза",
            "next_category": "Следующая категория",
            "prev_category": "Предыдущая категория",
            "stop": "Остановить воспроизведение",
            "toggle_hold": "Переключить 'Удерживать (Hold)'"
        }
        
        self.hotkey_vars = {}
        row_idx = 6
        for action_name, display_name in self.hotkey_actions.items():
            lbl = ctk.CTkLabel(tab_sp, text=f"{display_name}:")
            lbl.grid(row=row_idx, column=0, padx=20, pady=5, sticky="w")
            
            current_note = self.config_manager.get_global_hotkeys().get(action_name)
            var = ctk.StringVar(value=f"Нота {current_note}" if current_note is not None else "Не назначено")
            self.hotkey_vars[action_name] = var
            
            val_lbl = ctk.CTkLabel(tab_sp, textvariable=var, width=100)
            val_lbl.grid(row=row_idx, column=1, padx=(0, 10), pady=5, sticky="w")
            
            btn_frame = ctk.CTkFrame(tab_sp, fg_color="transparent")
            btn_frame.grid(row=row_idx, column=2, padx=(0, 20), pady=5, sticky="e")
            
            assign_btn = ctk.CTkButton(btn_frame, text="bind", width=60, 
                                       command=lambda a=action_name: self.listen_for_hotkey(a))
            assign_btn.pack(side="left", padx=(0, 5))
            
            clear_btn = ctk.CTkButton(btn_frame, text="✖", width=30, fg_color="#c0392b", hover_color="#e74c3c",
                                      command=lambda a=action_name: self.clear_hotkey(a))
            clear_btn.pack(side="left")
            
            row_idx += 1

        self.hotkey_status_label = ctk.CTkLabel(tab_sp, text="", text_color="orange")
        self.hotkey_status_label.grid(row=row_idx, column=0, columnspan=3, pady=5)
        
        # --- Macros Tab ---
        self.macros_frame = ctk.CTkScrollableFrame(tab_mac, fg_color="transparent")
        self.macros_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.macros_frame.grid_columnconfigure(1, weight=1)
        tab_mac.grid_rowconfigure(0, weight=1)
        
        macro_add_frame = ctk.CTkFrame(tab_mac, fg_color="transparent")
        macro_add_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        self.new_macro_note_var = ctk.StringVar(value="[MIDI Note]")
        self.new_macro_keys_var = ctk.StringVar(value="")
        
        self.macro_assign_btn = ctk.CTkButton(macro_add_frame, text="Assign MIDI", width=100, command=self.listen_for_macro_hotkey)
        self.macro_assign_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.macro_note_lbl = ctk.CTkLabel(macro_add_frame, textvariable=self.new_macro_note_var, width=80)
        self.macro_note_lbl.grid(row=0, column=1, padx=(0, 10))
        
        self.macro_keys_btn = ctk.CTkButton(macro_add_frame, text="Record Keys", width=120, command=self.record_macro_keys)
        self.macro_keys_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.macro_save_btn = ctk.CTkButton(macro_add_frame, text="Add Macro", width=80, command=self.add_macro)
        self.macro_save_btn.grid(row=0, column=3)
        
        self.macro_status_label = ctk.CTkLabel(tab_mac, text="", text_color="orange")
        self.macro_status_label.grid(row=2, column=0, pady=5)
        
        self.load_macros_ui()
        
        # --- About Tab ---
        about_frame = ctk.CTkFrame(tab_about, fg_color="transparent")
        about_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        author_lbl = ctk.CTkLabel(about_frame, text="Автор приложения - Дмитрий Кошелев", font=ctk.CTkFont(size=14, weight="bold"))
        author_lbl.pack(pady=(20, 10))
        
        vk_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        vk_frame.pack(pady=5)
        ctk.CTkLabel(vk_frame, text="Вк: ").pack(side="left")
        vk_lbl = ctk.CTkLabel(vk_frame, text="https://vk.com/cupofmilk11", text_color="#1DA1F2", cursor="hand2")
        vk_lbl.pack(side="left")
        vk_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://vk.com/cupofmilk11"))
        
        tg_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        tg_frame.pack(pady=5)
        ctk.CTkLabel(tg_frame, text="tg: ").pack(side="left")
        tg_lbl = ctk.CTkLabel(tg_frame, text="@cupofmilk11", text_color="#1DA1F2", cursor="hand2")
        tg_lbl.pack(side="left")
        tg_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/cupofmilk11"))
        
        
        # Save Button (Global)
        self.save_btn = ctk.CTkButton(self, text="Save & Close", command=self.save_and_close)
        self.save_btn.grid(row=1, column=0, pady=(0, 20))

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)

    def browse_exe(self):
        file_path = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")])
        if file_path:
            self.exe_entry.delete(0, "end")
            self.exe_entry.insert(0, file_path)

    def listen_for_hotkey(self, action):
        """Tells the main app to route the next MIDI signal here."""
        self.hotkey_status_label.configure(text=f"Waiting: Press a key for '{self.hotkey_actions[action]}'...")
        self.master.assigning_global_hotkey = action

    def on_hotkey_received(self, action, note):
        """Called by main App when a key is pressed during assign mode."""
        if action == "macro_assign":
            self.new_macro_note_var.set(f"Note {note}")
            self.macro_status_label.configure(text=f"Ready to add macro for Note {note}", text_color="green")
            self.master.assigning_global_hotkey = None
            return
            
        self.config_manager.set_global_hotkey(action, note)
        self.hotkey_vars[action].set(f"Note {note}")
        self.hotkey_status_label.configure(text=f"Assigned Note {note} to '{self.hotkey_actions[action]}'", text_color="green")
        self.master.assigning_global_hotkey = None

    def clear_hotkey(self, action):
        self.config_manager.remove_global_hotkey(action)
        self.hotkey_vars[action].set("Not assigned")
        self.hotkey_status_label.configure(text=f"Cleared hotkey for '{self.hotkey_actions[action]}'", text_color="gray")
        if getattr(self.master, 'assigning_global_hotkey', None) == action:
            self.master.assigning_global_hotkey = None

    def load_macros_ui(self):
        for widget in self.macros_frame.winfo_children():
            widget.destroy()
            
        macros = self.config_manager.get_custom_macros()
        for idx, (note_str, keys) in enumerate(macros.items()):
            lbl = ctk.CTkLabel(self.macros_frame, text=f"Note {note_str} ➜ {keys}")
            lbl.grid(row=idx, column=0, padx=10, pady=5, sticky="w")
            
            del_btn = ctk.CTkButton(self.macros_frame, text="✖", width=30, fg_color="#c0392b", hover_color="#e74c3c",
                                    command=lambda n=note_str: self.delete_macro(n))
            del_btn.grid(row=idx, column=1, padx=10, pady=5, sticky="e")
            
    def listen_for_macro_hotkey(self):
        self.macro_status_label.configure(text="Waiting: Press a key for Macro...")
        self.master.assigning_global_hotkey = "macro_assign"
        
    def record_macro_keys(self):
        self.macro_status_label.configure(text="Listening... Press a combo on your PC keyboard.", text_color="orange")
        self.macro_keys_btn.configure(state="disabled", text="Recording...")
        
        def _listen():
            import keyboard
            # Wait for user to press keys, then return combo
            try:
                combo = keyboard.read_hotkey(suppress=False)
                self.after(0, lambda: self._on_keys_recorded(combo))
            except Exception as e:
                self.after(0, lambda: self._on_keys_recorded("", error=str(e)))
                
        import threading
        threading.Thread(target=_listen, daemon=True).start()
        
    def _on_keys_recorded(self, combo, error=None):
        if error:
            self.macro_status_label.configure(text=f"Error reading keys: {error}", text_color="red")
            self.macro_keys_btn.configure(state="normal", text="Record Keys")
        else:
            self.new_macro_keys_var.set(combo)
            self.macro_keys_btn.configure(state="normal", text=combo if combo else "Record Keys")
            self.macro_status_label.configure(text=f"Recorded: {combo}", text_color="green")

    def add_macro(self):
        note = self.new_macro_note_var.get().replace("Note ", "")
        keys = self.new_macro_keys_var.get().strip()
        if note == "[MIDI Note]" or not note:
            self.macro_status_label.configure(text="Error: Assign MIDI note first", text_color="red")
            return
        if not keys:
            self.macro_status_label.configure(text="Error: Record a keyboard shortcut first", text_color="red")
            return
            
        self.config_manager.set_custom_macro(note, keys)
        self.load_macros_ui()
        self.new_macro_note_var.set("[MIDI Note]")
        self.macro_status_label.configure(text="Macro added successfully!", text_color="green")
        
    def delete_macro(self, note_str):
        self.config_manager.remove_custom_macro(note_str)
        self.load_macros_ui()

    def save_and_close(self):
        # Save general settings
        new_folder = self.folder_entry.get().strip()
        new_exe = self.exe_entry.get().strip()
        new_auto_start = self.auto_start_var.get()
        new_steam_start = self.steam_start_var.get()
        
        self.config_manager.set_soundpad_data_folder(new_folder)
        self.config_manager.set_soundpad_exe_path(new_exe)
        self.config_manager.set_auto_start_soundpad(new_auto_start)
        self.config_manager.set_soundpad_via_steam(new_steam_start)
        
        if getattr(self.master, 'assigning_global_hotkey', None):
            self.master.assigning_global_hotkey = None
            
        if self.on_close_callback:
            self.on_close_callback()
        
        self.destroy()
