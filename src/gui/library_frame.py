
import customtkinter as ctk
import os
import glob
from src.soundpad.parser import SoundpadParser

class LibraryFrame(ctk.CTkFrame):
    def __init__(self, master, config_manager, on_sound_selected=None, on_play_sound=None, on_bind_playing=None, on_select_soundpad=None, on_api_sync_request=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.config_manager = config_manager
        self.on_sound_selected = on_sound_selected # Callback(sound_data)
        self.on_play_sound = on_play_sound # Callback(sound_index)
        self.on_bind_playing = on_bind_playing # Callback(sound_data)
        self.on_select_soundpad = on_select_soundpad # Callback(sound_index)
        self.on_api_sync_request = on_api_sync_request # Callback() -> triggers App to fetch from API
        self.parser = SoundpadParser()
        
        self.is_edit_mode = False
        self.selected_sound = None
        
        # Layout: Left column (Categories), Right column (Sounds)
        self.grid_columnconfigure(0, weight=1) # Categories
        self.grid_columnconfigure(1, weight=2) # Sounds
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Content
        
        # --- Categories ---
        # Header (Placeholder to align with sounds)
        self.cat_header = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.cat_header.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        ctk.CTkLabel(self.cat_header, text="Categories", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=5)
        
        # Refresh Button
        ctk.CTkButton(self.cat_header, text="↻", width=30, command=self.refresh, 
                      fg_color="gray", hover_color="gray40").pack(side="right", padx=5)

        # List
        self.cat_frame = ctk.CTkScrollableFrame(self)
        self.cat_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=0)
        
        # --- Sounds ---
        # Header with Edit Toggle
        self.sound_header = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.sound_header.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=(0, 5))
        
        ctk.CTkLabel(self.sound_header, text="Sounds", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=5)
        
        # Edit Toggle Button (Pencil)
        # Using a button that changes color/text state
        self.edit_btn = ctk.CTkButton(self.sound_header, text="✎ Edit Mode: OFF", width=120, 
                                      command=self.toggle_edit_mode, 
                                      fg_color="gray", hover_color="gray40")
        self.edit_btn.pack(side="right", padx=5)

        # Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_sounds())
        self.search_entry = ctk.CTkEntry(self.sound_header, placeholder_text="Search...", textvariable=self.search_var, width=150)
        self.search_entry.pack(side="left", padx=5)

        # List
        self.sound_frame = ctk.CTkScrollableFrame(self)
        self.sound_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=0)
        
        self.categories_data = [] # List of {name, sounds}
        self.selected_category_index = -1
        
        self.refresh()

    def toggle_edit_mode(self):
        self.is_edit_mode = not self.is_edit_mode
        if self.is_edit_mode:
            self.edit_btn.configure(text="✎ Edit Mode: ON", fg_color="red", hover_color="darkred")
        else:
            self.edit_btn.configure(text="✎ Edit Mode: OFF", fg_color="gray", hover_color="gray40")

    def refresh(self):
        """Scans folder and reloads data."""
        # Clear UI
        for w in self.cat_frame.winfo_children(): w.destroy()
        for w in self.sound_frame.winfo_children(): w.destroy()
        
        folder = self.config_manager.get_soundpad_data_folder()
        if not folder or not os.path.exists(folder):
            ctk.CTkLabel(self.cat_frame, text="No folder selected.\nGo to Settings.").pack(pady=20)
            return

        # Scan for XMLs and SPLs
        # Priority: soundlist.spl > soundlist.xml > others
        # We should only load ONE valid database file to avoid duplicates, 
        # unless the user has split configs (unlikely for Soundpad).
        
        target_file = None
        priority_files = ["soundlist.spl", "soundlist.xml"]
        
        for pf in priority_files:
            full_path = os.path.join(folder, pf)
            if os.path.exists(full_path):
                 target_file = full_path
                 break
        
        # If not found standard files, look for any .spl or .xml and pick first?
        # Or maybe the user *wants* to see everything? 
        # User said "repeated folders", implying we loaded multiple files with same content.
        # Let's stick to single source of truth.
        
        if not target_file:
            spls = glob.glob(os.path.join(folder, "**/*.spl"), recursive=True)
            if spls:
                target_file = spls[0]
            else:
                xmls = glob.glob(os.path.join(folder, "**/*.xml"), recursive=True)
                if xmls:
                    target_file = xmls[0]
        
        if target_file:
             self.categories_data = self.parser.parse_file(target_file)
        else:
             self.categories_data = []
        
        # Populate Categories
        if not self.categories_data:
             ctk.CTkLabel(self.cat_frame, text="No sounds found.").pack(pady=20)
             return

        # Keep track of expanded state: category path -> bool
        if not hasattr(self, 'expanded_categories'):
            self.expanded_categories = {}

        self._render_category_tree(self.categories_data, self.cat_frame, level=0)

        # Select first by default if nothing selected (using a flat index or just picking the first category)
        # We need a flat list of categories to maintain existing selection logic
        if self.categories_data and getattr(self, "selected_category_index", -1) < 0:
            self.select_category(0, self.categories_data[0])

        # After local load, trigger API sync to grab any "new" sounds not in the .spl
        if self.on_api_sync_request:
            self.on_api_sync_request()

    def load_api_sounds(self, api_sounds_list):
        """Injects a flat list of sounds from the Soundpad API into the category tree."""
        if not api_sounds_list:
            return

        # 1. Collect all existing sound titles (case-insensitive) to avoid duplicates
        existing_titles = set()
        def _collect(categories):
            for c in categories:
                # Ignore the "Новые" category itself if it exists during re-render
                if c.get('name') == "🆕 Новые":
                    continue
                for s in c.get('sounds', []):
                    existing_titles.add(s.get('title', '').strip().lower())
                _collect(c.get('subcategories', []))
        
        _collect(getattr(self, 'categories_data', []))

        # 2. Add only sounds that aren't in the loaded SPL
        formatted_sounds = []
        for s in api_sounds_list:
            title = s.get('title', 'Unknown')
            if title.strip().lower() not in existing_titles:
                formatted_sounds.append({
                    'title': title,
                    'api_index': s.get('index', s.get('api_index', 0)),
                    'index': s.get('index', '') # Keep for backward compatibility
                })

        # Remove existing API category if it exists to replace it
        self.categories_data = [cat for cat in getattr(self, 'categories_data', []) if cat.get('name') != "🆕 Новые"]

        # Only create the category if there are actually any NEW sounds
        if formatted_sounds:
            api_category = {
                'name': "🆕 Новые",
                'path': "api_sync",
                'sounds': formatted_sounds,
                'subcategories': []
            }
            
            # Put it at the top
            self.categories_data.insert(0, api_category)
            
            if not hasattr(self, 'expanded_categories'):
                self.expanded_categories = {}
            self.expanded_categories["api_sync"] = True

        # Redraw UI
        for w in self.cat_frame.winfo_children(): w.destroy()
        self._render_category_tree(self.categories_data, self.cat_frame, level=0)

    def _render_category_tree(self, categories_list, parent_frame, level=0):
        # We need to flatten the list to assign correct indices for the existing `select_category`
        # However, to avoid rewriting entire selection logic right now, we can pass the actual category dict
        # and store it instead of just an index.
        # Let's map categories to a flat list for index compatibility
        if level == 0:
            self.flat_categories = []
            if not hasattr(self, 'category_buttons'):
                self.category_buttons = {}
            else:
                self.category_buttons.clear()

        indent = level * 15
        
        for cat in categories_list:
            current_index = len(self.flat_categories)
            self.flat_categories.append(cat)
            
            # Container for row
            row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=1, padx=(indent, 0))
            
            has_children = len(cat.get('subcategories', [])) > 0
            
            # Toggle Button (if has children)
            if has_children:
                is_expanded = self.expanded_categories.get(cat['path'], False)
                toggle_text = "▼" if is_expanded else "▶"
                toggle_btn = ctk.CTkButton(row_frame, text=toggle_text, width=20, height=20,
                                           fg_color="transparent", text_color="gray", hover_color="gray30",
                                           command=lambda c=cat: self.toggle_category(c['path']))
                toggle_btn.pack(side="left")
            else:
                # Spacer to align text with folders that have toggle buttons
                ctk.CTkFrame(row_frame, width=20, height=20, fg_color="transparent").pack(side="left")

            # Main Category Button
            btn = ctk.CTkButton(row_frame, text=cat['name'], anchor="w",
                                command=lambda idx=current_index, c=cat: self.select_category(idx, c),
                                fg_color="transparent", text_color=("gray10", "gray90"), hover_color="gray80")
            btn.pack(side="left", fill="x", expand=True)
            self.category_buttons[current_index] = btn

            # Recurse if expanded
            if has_children and self.expanded_categories.get(cat['path'], False):
                self._render_category_tree(cat['subcategories'], parent_frame, level + 1)

    def toggle_category(self, path):
        self.expanded_categories[path] = not self.expanded_categories.get(path, False)
        
        # Redraw categories
        for w in self.cat_frame.winfo_children(): w.destroy()
        self._render_category_tree(self.categories_data, self.cat_frame, level=0)

    def select_category(self, index, category_dict=None):
        self.selected_category_index = index
        self.selected_category_data = category_dict
        
        # Highlight logic
        if hasattr(self, 'category_buttons'):
            for idx, btn in self.category_buttons.items():
                if btn.winfo_exists():
                    if idx == index:
                        # Highlight active category
                        btn.configure(text_color="#3498db", font=ctk.CTkFont(weight="bold"))
                    else:
                        # Reset inactive categories
                        btn.configure(text_color=("gray10", "gray90"), font=ctk.CTkFont(weight="normal"))

        self.refresh_sounds()
        
    def refresh_sounds(self):
        # Populate Sounds
        for w in self.sound_frame.winfo_children(): w.destroy()
        
        if not self.categories_data or getattr(self, 'selected_category_data', None) is None:
            return

        query = self.search_var.get().strip().lower()

        sounds_to_show = []
        if query:
            # Search across ALL categories recursively
            def _find_sounds(cat_list):
                for cat in cat_list:
                    for sound in cat['sounds']:
                        if query in sound['title'].lower():
                            sounds_to_show.append(sound)
                    if 'subcategories' in cat:
                        _find_sounds(cat['subcategories'])
            
            _find_sounds(self.categories_data)
        else:
            # Show only selected category
            sounds_to_show = self.selected_category_data['sounds']

        # Limit to 100 results to prevent UI lag on empty query or large search
        for i, sound in enumerate(sounds_to_show):
            if i >= 200:
                ctk.CTkLabel(self.sound_frame, text="... too many results, keep typing ...").pack(pady=5)
                break

            # Create a Frame for each item to handle events better
            item_frame = ctk.CTkFrame(self.sound_frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=1)
            
            # Label for text
            lbl = ctk.CTkLabel(item_frame, text=sound['title'], anchor="w", padx=5)
            lbl.pack(fill="both", expand=True)
            
            # Bind events to both Frame and Label
            # Single click to select
            item_frame.bind("<Button-1>", lambda e, s=sound, f=item_frame: self.on_click_sound(s, f))
            lbl.bind("<Button-1>", lambda e, s=sound, f=item_frame: self.on_click_sound(s, f))
            
            # Double click to play
            item_frame.bind("<Double-1>", lambda e, s=sound: self.play_sound(s))
            lbl.bind("<Double-1>", lambda e, s=sound: self.play_sound(s))
            
            # Hover effects (manual since not a button)
            def on_enter(e, f=item_frame): f.configure(fg_color=("gray85", "gray25"))
            def on_leave(e, f=item_frame): 
                # Keep request color if selected? For now just revert.
                if self.selected_sound_frame != f:
                    f.configure(fg_color="transparent")
                else:
                    f.configure(fg_color=("gray75", "gray20")) # Selected color

            item_frame.bind("<Enter>", on_enter)
            item_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            
            # Context Menu (Right Click)
            item_frame.bind("<Button-3>", lambda e, s=sound: self.show_sound_context_menu(e, s))
            lbl.bind("<Button-3>", lambda e, s=sound: self.show_sound_context_menu(e, s))
    
    selected_sound_frame = None

    def show_sound_context_menu(self, event, sound):
        import tkinter as tk
        import subprocess
        
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", 
                       activebackground="#1f538d", activeforeground="white", 
                       relief="flat", borderwidth=0)
        menu.add_command(label=f"Sound: {sound['title']}", state="disabled")
        menu.add_separator()
        
        # 0) Play
        menu.add_command(label="▶ Воспроизвести", 
                         command=lambda: self.play_sound(sound))
                         
        # 1) Bind to key
        menu.add_command(label="⌨ Привязать к клавише (Выбор на клавиатуре)", 
                         command=lambda: self.request_bind_playing(sound))
        
        # 2) Open in explorer
        menu.add_command(label="📂 Открыть в проводнике",
                         command=lambda: self.open_in_explorer(sound.get('url')))
                         
        # 3) Open in Soundpad
        menu.add_command(label="🎵 Выбрать в Soundpad",
                         command=lambda: self.select_in_soundpad(sound))
                         
        # 4) Show in Folder (Navigate Library Frame)
        menu.add_command(label="🔍 Показать в папке (здесь)",
                         command=lambda: self.navigate_to_category(sound.get('category_path')))
                         
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def request_bind_playing(self, sound):
        # Triggers a callback so the App can intercept the next keyboard click
        if hasattr(self, 'on_bind_playing') and self.on_bind_playing:
            self.on_bind_playing(sound)

    def open_in_explorer(self, url):
        import subprocess
        import os
        if url and os.path.exists(url):
            subprocess.Popen(f'explorer /select,"{os.path.abspath(url)}"')
            
    def select_in_soundpad(self, sound):
        # Requires SoundpadClient. We do not have direct access to it here unless passed.
        # But we do have self.on_play_sound which passes index. Let's create an event or callback.
        # However, for now, we rely on App registering a callback.
        # Let's add a `on_select_soundpad` callback. For now, try to get index and emit event.
        if hasattr(self, 'on_select_soundpad') and self.on_select_soundpad:
            idx = sound.get('api_index') or sound.get('index')
            if idx:
                self.on_select_soundpad(int(idx))

    def navigate_to_category(self, target_path):
        if not target_path: return
        
        # 1. Expand all parent categories to make it visible
        parts = target_path.split(" / ")
        current = ""
        for part in parts[:-1]: # Don't expand the leaf yet
            current = f"{current} / {part}" if current else part
            self.expanded_categories[current] = True
            
        # 2. Redraw to apply expansions
        for w in self.cat_frame.winfo_children(): w.destroy()
        self._render_category_tree(self.categories_data, self.cat_frame, level=0)
        
        # 3. Find index and select
        for idx, cat in enumerate(self.flat_categories):
            if cat['path'] == target_path:
                self.select_category(idx, cat)
                # Clear search to show the category
                self.search_var.set("")
                break

    def on_click_sound(self, sound, frame):
        # Update visual selection
        if self.selected_sound_frame:
            self.selected_sound_frame.configure(fg_color="transparent")
        
        self.selected_sound_frame = frame
        frame.configure(fg_color=("gray75", "gray20"))
        
        self.select_sound(sound)

    def select_sound(self, sound):
        self.selected_sound = sound
        if self.on_sound_selected:
            self.on_sound_selected(sound)

    def play_sound(self, sound):
        if self.on_play_sound:
            # Check if 'api_index' exists (added by parser), else try 'index'
            idx = sound.get('api_index') or sound.get('index')
            if idx:
                self.on_play_sound(int(idx))
