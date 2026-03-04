# MatchaCheck

A Python desktop app that stares at your webcam and decides if you're holding matcha. If you are — congrats, you're *performative*, and here's a Spotify track to prove it.

## What It Does

MatchaCheck uses a custom-trained YOLOv8 model to detect matcha drinks through your webcam in real time. The default state is always "Not Performative." The **only** thing that flips it to "PERFORMATIVE" is matcha — not coffee, not green juice, not your green phone case. When it detects matcha, it automatically opens a Spotify track because vibes matter.

## Demo

![demo](demo.gif)

## How It Works

- Grabs frames from your webcam at ~30 FPS
- Runs each frame through a YOLOv8 model (default: yolov8n.pt with HSV color detection)
- You can switch to your own custom-trained model (best.pt) using the toggle button in the app
- If the model detects matcha with >60% confidence → you're PERFORMATIVE
- Spotify playback kicks in automatically — Premium users get API control, Free users get the app opened

## Tech Stack

- **Python** - The whole thing  
- **PyQt6** - Desktop GUI with live webcam feed  
- **OpenCV** - Webcam capture and image processing  
- **YOLOv8** - Object detection (with custom-trained model)  
- **MediaPipe HandLandmarker** - Real-time hand tracking overlay (optional) 
- **spotipy** - Spotify Web API wrapper  
- **Spotify Web API** - Playback control for Premium users
- **HSV Masking** - Fallback color-based detection

## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/rvnztolentino/matchacheck.git
   cd matchacheck
   ```
2. Create a virtual environment and activate it
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Spotify credentials
   ```bash
   cp .env.example .env
   ```
5. Run it
   ```bash
   python main.py
   ```
6. Make sure your trained YOLOv8 model (`best.pt`) is saved in the `model/` directory

## How to Set Your Spotify Track

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an app
2. Set the redirect URI to `http://127.0.0.1:8888/callback`
3. Copy your Client ID and Client Secret into `.env`
4. Grab the URL of any Spotify track and paste it into `SPOTIFY_PERFORMATIVE_URL`
5. For Premium users: also paste the `spotify:track:...` URI into `SPOTIFY_PERFORMATIVE_URI`

## Spotify Free vs Premium

If you're on Spotify Free, MatchaCheck will open your track in the Spotify app (or browser) when matcha is detected. If you're on Premium, it uses the Spotify Web API to start playback directly on your active device — no window switching needed. Either way, you get music.
