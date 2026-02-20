import os
import subprocess
import sys

def main():
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    print("Running PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MidiToPad",
        "--onefile",
        "--noconsole",
        "--clean",
        "--collect-all=customtkinter",
    ]
    
    # Добавляем иконку, если она существует
    if os.path.exists("icon.ico"):
        cmd.extend(["--icon=icon.ico", "--add-data=icon.ico;."])
        print("Using and embedding icon.ico for the executable.")
    
    cmd.append("main.py")
    
    subprocess.check_call(cmd)
    
    print("Build complete! Check the 'dist' folder for MidiToPad.exe")

if __name__ == "__main__":
    main()
