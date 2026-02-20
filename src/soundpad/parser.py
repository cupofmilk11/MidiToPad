
import xml.etree.ElementTree as ET
import logging
import os

class SoundpadParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path):
        """
        Parses a Soundpad XML/SPL file.
        Returns a structure:
        [
            {'name': 'Category Name', 'sounds': [{'title': 'Sound Title', 'url': 'Path', ...}, ...]},
            ...
        ]
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return []

        try:
            # .spl files are XML but with a different extension. 
            # They might have encoding issues or binary headers?
            # Usually strict XML parsers work if it's pure XML.
            # If fail, try to read as text and clean up?
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Check root tag to determine format
            # Standard soundlist.xml usually has <Soundlist> root and flat <Sound> list? 
            # Or <Categories>? Let's try to handle both or generic probing.
            
            # Based on previous debug, get_sound_list returned <Soundlist><Sound .../></Soundlist> (flat).
            # If exported file preserves categories, it might look different.
            # If soundlist.xml is being read, it might have <Database> or similar.
            
            # Hypothesis from similar apps:
            # <Soundpad>
            #   <Soundlist>...</Soundlist>
            #   <Categories>
            #       <Category id="..." name="...">
            #           <Sound idRef="..."/>
            #       </Category>
            #   </Categories>
            # </Soundpad>
            
            categories = []
            
            # 1. Parse all "Sound" elements directly under root (Soundlist)
            # They don't have IDs usually, they are referenced by position (index).
            # API uses 1-based index. SPL 'id' attribute in categories uses 0-based index.
            
            all_sounds = {} # Map by 0-based index (int) -> Sound Data
            
            # Find direct Sound children of root
            # root.findall("Sound") might work if root is Soundlist
            sound_elements = root.findall("Sound")
            
            if not sound_elements:
                 # Try finding Soundlist tag if root is NOT Soundlist (e.g. wrapper)
                 sl = root.find("Soundlist")
                 if sl:
                     sound_elements = sl.findall("Sound")
            
            for idx, sound_elem in enumerate(sound_elements):
                sound_data = sound_elem.attrib
                # Ensure title exists
                if 'title' not in sound_data or not sound_data['title']:
                    # Fallback to basename of url
                    url = sound_data.get('url', '')
                    if url:
                         sound_data['title'] = os.path.basename(url)
                    else:
                         sound_data['title'] = "Unknown Sound"
                
                # Assign 1-based index for API usage
                sound_data['api_index'] = idx + 1
                
                # Store by 0-based index for Category linking
                all_sounds[str(idx)] = sound_data
                
                # Also store by explicit 'index' or 'id' if present (for exported XMLs)
                if 'index' in sound_data:
                     all_sounds[sound_data['index']] = sound_data
                if 'id' in sound_data:
                     all_sounds[sound_data['id']] = sound_data


            # 2. Look for Categories
            # Categories are usually under <Categories> tag, which is a child of <Soundlist> (root)
            categories_tag = root.find("Categories")
            if categories_tag is None and root.tag != "Soundlist":
                 # Maybe root is wrapper
                 sl = root.find("Soundlist")
                 if sl:
                     categories_tag = sl.find("Categories")

            def _parse_category(cat_elem, path=""):
                cat_name = cat_elem.get('name', 'Unnamed Category')
                current_path = f"{path} / {cat_name}" if path else cat_name
                
                cat_sounds = []
                # Sounds in category define 'id' which maps to index
                for sound_ref in cat_elem.findall("Sound"):
                    ref_id = sound_ref.get('id')
                    sound_obj = None
                    if ref_id in all_sounds:
                        sound_obj = all_sounds[ref_id]
                    else:
                        try:
                            if str(int(ref_id)) in all_sounds:
                                 sound_obj = all_sounds[str(int(ref_id))]
                        except:
                            pass
                    
                    if sound_obj:
                        # Add category path to the sound object for "Show in Folder" feature later
                        # Make a shallow copy so the same sound in "All Sounds" doesn't get a specific path overridden
                        sound_copy = sound_obj.copy()
                        sound_copy['category_path'] = current_path
                        cat_sounds.append(sound_copy)

                subcategories = []
                for sub_elem in cat_elem.findall("Category"):
                    if sub_elem.get('name', 'Unnamed Category') == 'Unnamed Category':
                        continue
                    subcategories.append(_parse_category(sub_elem, current_path))

                return {
                    'name': cat_name,
                    'path': current_path,
                    'sounds': cat_sounds,
                    'subcategories': subcategories
                }

            if categories_tag is not None:
                for cat_elem in categories_tag.findall("Category"):
                    # Игнорируем техническую папку Soundpad
                    if cat_elem.get('name', 'Unnamed Category') == 'Unnamed Category':
                        continue
                    categories.append(_parse_category(cat_elem))
            
            # Add "All Sounds" category at the end or beginning
            all_sounds_list = [all_sounds[str(i)] for i in range(len(sound_elements)) if str(i) in all_sounds]
            if not categories or (len(categories) == 0):
                # If no categories found (e.g. export file), try existing logic or just ALL
                categories.append({'name': 'All Sounds', 'path': 'All Sounds', 'sounds': all_sounds_list, 'subcategories': []})
            
            # Always add All Sounds? User might want it.
            # User request: "Убери из папок all sounds"
            # categories.append({'name': 'All Sounds', 'path': 'All Sounds', 'sounds': all_sounds_list, 'subcategories': []})
            
            return categories

        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
            return []
