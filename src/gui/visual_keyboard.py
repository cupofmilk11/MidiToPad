
import customtkinter as ctk
import tkinter as tk

class VisualKeyboard(ctk.CTkFrame):
    def __init__(self, master, start_octave=3, num_octaves=2, max_height_limit=533, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        
        self.start_octave = start_octave
        self.num_octaves = num_octaves
        self.max_height_limit = max_height_limit
        
        # Dimensions (Calculated dynamically)
        self.total_white_keys = self.num_octaves * 7
        self.white_key_width = 40 # Default backup
        self.white_key_height = 200
        self.black_key_width = 24
        self.black_key_height = 120
        
        self.canvas = ctk.CTkCanvas(self, height=self.white_key_height, bg="gray20", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Bind resize
        self.bind("<Configure>", self.on_resize)
        
        # Callbacks
        self.on_key_click = None # Function(note)
        self.on_key_context = None # Function(note, event)
        
        # Persistent state for notes (survives redraw/resize)
        # note_number -> {'label': str, 'color': hex/None}
        self.note_data = {} 
        
        self.draw_keyboard()

        # Bindings
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_context)

    def _get_contrasting_text_color(self, hex_color):
        """Returns 'black' or 'white' depending on background brightness."""
        if not hex_color: return "black"
        if hex_color.startswith("#"):
            hex_color = hex_color.lstrip('#')
            try:
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                # Brightness formula
                brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                return "black" if brightness > 128 else "white"
            except:
                return "black"
        # Handle standard names
        if hex_color.lower() in ["white", "ivory", "yellow"]: return "black"
        if hex_color.lower() in ["black", "darkblue", "purple"]: return "white"
        return "black" # Default
        
    def on_resize(self, event):
        self.draw_keyboard()

    def set_start_octave(self, octave):
        """Sets the starting octave and redraws."""
        if octave < 0: octave = 0
        if octave > 8: octave = 8 # Max limit
        
        if self.start_octave != octave:
            self.start_octave = octave
            self.draw_keyboard()

    def shift_octave(self, delta):
        self.set_start_octave(self.start_octave + delta)

    def _create_rounded_bottom_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Draws a rectangle with rounded bottom corners using a polygon."""
        import math
        points = []
        
        # Top-left corner (sharp)
        points.extend([x1, y1])
        # Top-right corner (sharp)
        points.extend([x2, y1])
        
        # Bottom-right corner (rounded)
        # We draw an arc from 0 to pi/2 (right to bottom)
        cx = x2 - radius
        cy = y2 - radius
        for i in range(11):
            angle = i * (math.pi / 2) / 10
            points.extend([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
            
        # Bottom-left corner (rounded)
        # We draw an arc from pi/2 to pi (bottom to left)
        cx = x1 + radius
        cy = y2 - radius
        for i in range(11):
            angle = math.pi / 2 + i * (math.pi / 2) / 10
            points.extend([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
            
        # Back to top-left happens automatically when polygon closes
        return self.canvas.create_polygon(points, smooth=False, **kwargs)

    def draw_keyboard(self):
        self.canvas.delete("all")
        self.keys = {}
        self.key_rects = {}
        
        # Calculate dynamic width
        current_width = self.winfo_width()
        current_height = self.winfo_height()
        
        # Limit height so it doesn't stretch indefinitely
        if current_height > self.max_height_limit:
            current_height = self.max_height_limit
            
        if current_width > 1:
            self.white_key_width = current_width / self.total_white_keys
            
        if current_height > 1:
            # Update canvas internal height so it doesn't clip
            self.canvas.configure(height=current_height)
            self.white_key_height = current_height
            self.black_key_height = current_height * 0.6 # Black keys are 60% of vertical space
        
        # Recalculate black key width proportional to white?
        # Standard: Black is usually ~60% of white width
        self.black_key_width = self.white_key_width * 0.6

        # White keys
        white_notes = [0, 2, 4, 5, 7, 9, 11] # Indices in octave
        # Black keys mapping: 1->C#, 3->D#, etc.
        black_notes = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5} # Note index -> offset from previous white key
        
        # Draw Whites first
        x = 0
        for oct_idx in range(self.num_octaves):
            current_oct = self.start_octave + oct_idx
            base_note = current_oct * 12
            
            for i in range(7): # 7 white keys
                # Determine midi note
                note_offset = white_notes[i]
                midi_note = base_note + note_offset
                
                rect = self._create_rounded_bottom_rect(
                    x, 0, x + self.white_key_width, self.white_key_height, radius=6,
                    fill="white", outline="black", tags=("key", f"key_{midi_note}")
                )
                self.keys[midi_note] = rect
                
                # Get persistent data
                data = self.note_data.get(midi_note, {})
                default_color = data.get('color') or "white"
                label_text = data.get('label', "")
                
                self.key_rects[rect] = {'note': midi_note, 'type': 'white', 'default_color': default_color}
                self.canvas.itemconfig(rect, fill=default_color)
                
                # Determine text color
                text_color = self._get_contrasting_text_color(default_color)
                
                # Add Label placeholder
                # If C key (i==0), show Octave label at TOP
                if i == 0:
                    self.canvas.create_text(
                        x + self.white_key_width/2, 15, # Top position
                        text=f"C{current_oct}", tags=("oct_label", f"oct_label_{midi_note}"), 
                        font=("Arial", 12, "bold"), fill=text_color
                    )
                
                # Sound Assignment Label (Bottom)
                self.canvas.create_text(
                    x + self.white_key_width/2, self.white_key_height - 20,
                    text=label_text, tags=("label", f"label_{midi_note}"), 
                    font=("Arial", 11), fill=text_color, width=self.white_key_width - 4, justify="center"
                )
                
                x += self.white_key_width
        
        # Draw Blacks on top
        x = 0
        for oct_idx in range(self.num_octaves):
            current_oct = self.start_octave + oct_idx
            base_note = current_oct * 12
            
            for i in range(7):
                current_white_note = white_notes[i]
                black_note_offset = current_white_note + 1
                
                if black_note_offset in black_notes:
                    # bx = x + self.white_key_width - (self.black_key_width / 2) 
                    # Use current dynamic width. x is start of NEXT white key loop? 
                    # Wait, loop logic above: x increments at end of loop.
                    # Inside loop, 'x' is start of THIS white key.
                    # Black key is AFTER this white key.
                    # So pos = x + white_width - black_width/2
                    
                    bx = x + self.white_key_width - (self.black_key_width / 2)
                    midi_note = base_note + black_note_offset
                    
                    rect = self._create_rounded_bottom_rect(
                        bx, 0, bx + self.black_key_width, self.black_key_height, radius=4,
                        fill="black", outline="black", tags=("key", f"key_{midi_note}")
                    )
                    self.keys[midi_note] = rect
                    
                    data = self.note_data.get(midi_note, {})
                    default_color = data.get('color') or "black"
                    label_text = data.get('label', "")
                    
                    text_color = self._get_contrasting_text_color(default_color)
                    
                    self.key_rects[rect] = {'note': midi_note, 'type': 'black', 'default_color': default_color}
                    self.canvas.itemconfig(rect, fill=default_color)
                    
                    self.canvas.create_text(
                        bx + self.black_key_width/2, self.black_key_height - 40,
                        text=label_text, tags=("label", f"label_{midi_note}"), 
                        fill=text_color, font=("Arial", 11), width=self.black_key_width - 4, justify="center"
                    )
                
                x += self.white_key_width

    def set_key_color(self, note, color):
        """Sets the permanent color of a key (overrides default white/black)."""
        # Store in persistent data
        if note not in self.note_data: self.note_data[note] = {}
        self.note_data[note]['color'] = color
        
        if note in self.keys:
            rect = self.keys[note]
            # If color is None, revert to black/white based on type
            if color is None:
                color = "white" if self.key_rects[rect]['type'] == 'white' else "black"
            
            self.key_rects[rect]['default_color'] = color
            self.canvas.itemconfig(rect, fill=color)
            
            # Update label color for contrast
            text_color = self._get_contrasting_text_color(color)
            self.canvas.itemconfig(f"label_{note}", fill=text_color)
            self.canvas.itemconfig(f"oct_label_{note}", fill=text_color)

    def set_key_label(self, note, text):
        """Sets the permanent label of a key."""
        if note not in self.note_data: self.note_data[note] = {}
        self.note_data[note]['label'] = text
        
        if note in self.keys:
            self.canvas.itemconfig(f"label_{note}", text=text)

    def highlight_key(self, note, on=True):
        if note in self.keys:
            rect = self.keys[note]
            info = self.key_rects[rect]
            # If on, use highlight color (blue). If off, use stored default_color (which might be custom)
            color = "#3498db" if on else info['default_color']
            self.canvas.itemconfig(rect, fill=color)
            self.update_idletasks()

    def _get_note_from_event(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item: return None
        item_id = item[0]
        
        # Try direct lookup first (if clicked on rect)
        if item_id in self.key_rects:
             return self.key_rects[item_id]['note']
             
        # Try parsing tags (if clicked on label)
        tags = self.canvas.gettags(item_id)
        for tag in tags:
            # Tag format: key_60, label_60, oct_label_60
            if "_" in tag:
                try:
                    # Split from right to handle potential underscores in prefix? 
                    # Prefixes are fixed: key, label, oct_label.
                    # Just split by last underscore
                    start, note_str = tag.rsplit("_", 1)
                    if start in ["key", "label", "oct_label"]:
                        return int(note_str)
                except ValueError:
                    pass
        return None

    def _on_click(self, event):
        note = self._get_note_from_event(event)
        if note is not None:
            if self.on_key_click:
                self.on_key_click(note)

    def _on_context(self, event):
        note = self._get_note_from_event(event)
        if note is not None:
             if self.on_key_context:
                self.on_key_context(note, event)
