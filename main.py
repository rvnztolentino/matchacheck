import sys
import os
from dotenv import load_dotenv

# Load variables from the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

from PyQt6.QtWidgets import QApplication
import spotify_player
from gui import MatchaCheckWindow

def main():
    """
    Entry point for MatchaCheck.
    Initializes the QApplication, wires up the modules, and runs the event loop.
    Never crashes silently, handles its own exceptions.
    """
    try:
        app = QApplication(sys.argv)
        
        # Initialize and show main window, passing down the spotify_player module
        window = MatchaCheckWindow(spotify_player)
        window.show()
        
        # Execute the Qt event loop
        sys.exit(app.exec())
    except Exception as e:
        print(f"MatchaCheck encountered a fatal error: {e}")

if __name__ == "__main__":
    main()
