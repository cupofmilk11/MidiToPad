
import os
import xml.etree.ElementTree as ET

def inspect_spl():
    path = os.path.join(os.getenv('APPDATA'), "Leppsoft", "soundlist.spl")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        # Try finding any spl in the folder
        folder = os.path.dirname(path)
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".spl"):
                    path = os.path.join(folder, f)
                    break
        
    if not os.path.exists(path):
        print("No .spl file found.")
        return

    print(f"Inspecting: {path}")
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        print(f"Root tag: {root.tag}")
        
        for child in root:
            print(f"  Child: {child.tag}, Attribs: {child.keys()}")
            if child.tag == "Soundlist":
                 for sound in child[:5]:
                     print(f"    Sound: {sound.tag}, Attrib: {sound.attrib}")
            if child.tag == "Categories":
                for cat in child[:5]:
                    print(f"    Category: {cat.attrib}")
                    for sub in cat[:5]:
                         print(f"      Sub: {sub.tag}, Attrib: {sub.attrib}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_spl()
