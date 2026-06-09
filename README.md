# MatchaCheck

MatchaCheck is a Python desktop app that watches your webcam for matcha-like green color. When matcha is detected, the app marks the moment as `PERFORMATIVE` and opens or controls a configured Spotify track.

## Tech Stack

- Python
- PyQt6 for the desktop interface
- OpenCV for webcam capture and image processing
- HSV color masking for matcha-like color detection
- MediaPipe HandLandmarker for optional hand overlay
- spotipy and Spotify Web API for playback control
- python-dotenv for local `.env` configuration

## Setup Instructions

1. Clone the repository.

   ```bash
   git clone https://github.com/rvnztolentino/matchacheck.git
   cd matchacheck
   ```

2. Create and activate a virtual environment.

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Upgrade `pip`.

   ```bash
   python -m pip install --upgrade pip
   ```

4. Install the project dependencies.

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Create your local environment file.

   ```bash
   cp .env.example .env
   ```

6. Edit `.env` with your Spotify settings.

## Configuration

MatchaCheck reads Spotify settings from `.env`.

```bash
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
SPOTIFY_PERFORMATIVE_URL=https://open.spotify.com/track/YOUR_TRACK_ID
SPOTIFY_PERFORMATIVE_URI=spotify:track:YOUR_TRACK_ID
```

Create a Spotify app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), then add `http://127.0.0.1:8888/callback` as the redirect URI.

`SPOTIFY_PERFORMATIVE_URL` is used to open Spotify in the app or browser. `SPOTIFY_PERFORMATIVE_URI` is used for direct playback through the Spotify Web API, which requires Spotify Premium and an active Spotify device.

## How to Run

Activate the virtual environment, install dependencies, then start the app:

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On first run, macOS may ask for camera permission. Allow access so the webcam feed can start.

## Notes

- Keep `model/hand_landmarker.task` in the `model/` directory if you want the optional hand overlay.
- Matcha detection is based on OpenCV HSV color masking.
- If you see `ModuleNotFoundError: No module named 'dotenv'`, install dependencies into the active virtual environment with `python -m pip install -r requirements.txt`.
- Spotify playback falls back to opening the configured track URL when direct Premium playback is unavailable.
