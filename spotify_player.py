import os
import webbrowser
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def play_performative():
    """
    Attempts to play Spotify playback for performative actions via Premium API.
    Silently falls back to opening a URL in the browser if it fails.
    Catches all exceptions to prevent crashing.
    """
    uri = os.environ.get("SPOTIFY_PERFORMATIVE_URI", "")
    url = os.environ.get("SPOTIFY_PERFORMATIVE_URL", "https://open.spotify.com/")
    
    try:
        # Initialize OAuth manager for spotipy
        scope = "user-modify-playback-state"
        manager = SpotifyOAuth(scope=scope)
        sp = spotipy.Spotify(auth_manager=manager)
        
        # Start playback
        if uri:
            # We attempt to play the context if it's a playlist/album, otherwise try as a track
            if "track" in uri:
                sp.start_playback(uris=[uri])
            else:
                sp.start_playback(context_uri=uri)
            print(f"Spotify Premium playback started for URI: {uri}")
        else:
            raise ValueError("No SPOTIFY_PERFORMATIVE_URI found in environment variables.")
            
    except Exception as e:
        print(f"Spotify Premium playback failed: {e}. Falling back to opening Spotify app...")
        # Fallback to opening the Spotify app directly instead of the browser
        try:
            import subprocess
            if uri:
                # On Mac, 'open' with a spotify URI launches the desktop app
                subprocess.run(["open", uri], check=True)
                print(f"Opened Spotify app with URI: {uri}")
            else:
                webbrowser.open(url)
                print(f"Opened Spotify URL in browser: {url}")
        except Exception as fallback_error:
            print(f"Fallback failed: {fallback_error}")

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
        print(f"Could not pause Spotify playback via API: {e}. Trying Mac fallback...")
        try:
            import subprocess
            subprocess.run(["osascript", "-e", 'tell application "Spotify" to pause'], check=True)
            print("Spotify playback paused via Mac script.")
        except Exception as mac_err:
            print(f"Mac fallback failed: {mac_err}")
