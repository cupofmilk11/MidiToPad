import time
from soundpad_control import SoundpadRemoteControl

s = SoundpadRemoteControl()

print("Stopping...")
s.stop_sound()
time.sleep(0.5)

print("Selecting row 2...")
s.select_row(2)

print("Playing...")
s.play_selected_sound()
time.sleep(1)

print("Stopping...")
s.stop_sound()
time.sleep(0.5)

print("Selecting row 3...")
s.select_row(3)

print("Playing...")
s.play_selected_sound()
