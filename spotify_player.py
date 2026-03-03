import os
import sys
import webbrowser
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def _spotify_app_installed():
    """
    Returns True if the Spotify desktop app appears to be installed.
    Checks Mac (/Applications/Spotify.app) and Windows (Registry).
    """
    if sys.platform == "darwin":
        return os.path.exists("/Applications/Spotify.app")
    elif sys.platform == "win32":
        try:
            import winreg
            winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Spotify",
            )
            return True
        except (ImportError, OSError):
            return False
    # Unsupported platform — assume not installed
    return False


def _open_with_app(uri):
    """Opens a Spotify URI using the desktop app (Mac/Windows)."""
    import subprocess
    if sys.platform == "darwin":
        subprocess.run(["open", uri], check=True)
    elif sys.platform == "win32":
        os.startfile(uri)  # Windows handles spotify: URIs natively


def play_performative():
    """
    Tries to start Spotify playback in this order:
    1. Spotify Premium Web API (instant, no window switch)
    2. Spotify desktop app (if installed)
    3. Browser fallback (if app not installed)
    Catches all exceptions to prevent crashing.
    """
    uri = os.environ.get("SPOTIFY_PERFORMATIVE_URI", "")
    url = os.environ.get("SPOTIFY_PERFORMATIVE_URL", "https://open.spotify.com/")

    # --- Attempt 1: Premium API ---
    try:
        scope = "user-modify-playback-state"
        manager = SpotifyOAuth(scope=scope)
        sp = spotipy.Spotify(auth_manager=manager)

        if uri:
            if "track" in uri:
                sp.start_playback(uris=[uri])
            else:
                sp.start_playback(context_uri=uri)
            print(f"Spotify Premium playback started for URI: {uri}")
        else:
            raise ValueError("No SPOTIFY_PERFORMATIVE_URI found in environment variables.")
        return  # success — done
    except Exception as e:
        print(f"Spotify Premium playback failed: {e}")

    # --- Attempt 2: Desktop app (if installed) ---
    if _spotify_app_installed():
        try:
            target = uri if uri else url
            _open_with_app(target)
            print(f"Opened Spotify app with: {target}")
            return
        except Exception as app_err:
            print(f"Spotify app launch failed: {app_err}")

    # --- Attempt 3: Browser fallback ---
    print("Spotify app not found — opening in browser.")
    webbrowser.open(url)
    print(f"Opened Spotify URL in browser: {url}")


def stop_playback():
    """
    Stops Spotify playback using Premium API.
    Does nothing if free account or if any error occurs.
    """
    try:
        scope = "user-modify-playback-state"
        manager = SpotifyOAuth(scope=scope)
        sp = spotipy.Spotify(auth_manager=manager)
        sp.pause_playback()
        print("Spotify playback paused.")
    except Exception as e:
        print(f"Could not pause Spotify playback via API: {e}. Trying app fallback...")
        try:
            import subprocess
            if sys.platform == "darwin":
                subprocess.run(
                    ["osascript", "-e", 'tell application "Spotify" to pause'],
                    check=True,
                )
                print("Spotify playback paused via AppleScript.")
            elif sys.platform == "win32":
                # Spotify on Windows doesn't have a simple CLI pause, nothing to do
                pass
        except Exception as mac_err:
            print(f"App fallback failed: {mac_err}")

