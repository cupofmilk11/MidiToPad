
try:
    from soundpad_control import SoundpadRemoteControl
    print(f"Type: {type(SoundpadRemoteControl)}")
    print(dir(SoundpadRemoteControl))
    
    # Check if we need to await init
    import inspect
    if inspect.iscoroutinefunction(SoundpadRemoteControl.__init__):
        print("__init__ is async")
    else:
        print("__init__ is sync")

except Exception as e:
    print(e)
