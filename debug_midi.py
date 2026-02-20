
import mido
import rtmidi

print(f"Mido version: {mido.__version__}")
print(f"RtMidi version: {rtmidi.__version__}")
print(f"Mido Backend: {mido.backend}")

print("\nAvailable APIs:")
for api in rtmidi.get_compiled_api():
    print(f"- {rtmidi.get_api_name(api)} ({api})")

print("\nInput Ports (mido.get_input_names()):")
for name in mido.get_input_names():
    print(f"- {name}")

print("\nInput Ports (rtmidi direct):")
try:
    midi_in = rtmidi.MidiIn()
    for port in midi_in.get_ports():
        print(f"- {port}")
except Exception as e:
    print(f"Error accessing rtmidi: {e}")
