
import logging
import sys
import os
from src.gui.app import App
def get_appdata_dir():
    appdata = os.getenv('APPDATA')
    if appdata:
        path = os.path.join(appdata, "MidiToPad")
    else:
        path = os.getcwd()
    os.makedirs(path, exist_ok=True)
    return path

# Configure logging to file
log_file = os.path.join(get_appdata_dir(), "app.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

if __name__ == "__main__":
    try:
        logger.info("Starting MidiToPad...")
        app = App()
        app.mainloop()
    except Exception as e:
        logger.critical(f"App crashed: {e}", exc_info=True)
