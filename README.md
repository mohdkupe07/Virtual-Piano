# 🎹 Hand Gesture Controlled Virtual Piano

A real-time virtual piano controlled entirely using hand gestures via webcam. Built using Python 3.11+, OpenCV, MediaPipe, NumPy, and Pygame.

## 📋 Project Overview

This project uses computer vision to detect hand landmarks from webcam feed and maps finger gestures to piano notes.

Just raise your fingers to play sounds — no keyboard required.

Finger Mapping:
Thumb = C  
Index = D  
Middle = E  
Ring = F  
Pinky = G  

Pinch gesture (Thumb + Index) is also detected.

## 🗂 Folder Structure

VirtualPiano/
├── main.py                 # Entry point  
├── hand_tracker.py        # MediaPipe hand tracking  
├── gesture_detector.py    # Finger & pinch detection  
├── piano_player.py        # Audio playback  
├── generate_sounds.py     # Generate .wav files  
├── requirements.txt       # Dependencies  
├── README.md  
└── sounds/
    ├── C.wav
    ├── D.wav
    ├── E.wav
    ├── F.wav
    └── G.wav

## ⚙️ Installation

Clone repository:
git clone <repo-url>
cd VirtualPiano

Create virtual environment:
python -m venv venv

Activate (Windows):
venv\Scripts\activate

Activate (Mac/Linux):
source venv/bin/activate

Install dependencies:
pip install -r requirements.txt

OR:
pip install opencv-python mediapipe numpy pygame

Generate sound files:
python generate_sounds.py

Run project:
python main.py

## 🎮 Controls

Thumb  → C  
Index  → D  
Middle → E  
Ring   → F  
Pinky  → G  

Pinch → Thumb + Index  
Quit → Q or ESC  

## 🧠 How It Works

MediaPipe detects 21 hand landmarks per hand.

Finger detection:
- If tip.y < pip.y → finger is UP (Index/Middle/Ring/Pinky)
- Thumb uses x-axis comparison based on left/right hand

## 🤏 Pinch Detection

distance = sqrt((x4-x8)^2 + (y4-y8)^2)

If distance < 40 pixels → pinch detected

## 🔁 Debounce Logic

Only triggers sound on state change:
DOWN → UP triggers note  
UP → UP ignored  

## 🎵 Audio System

Uses pygame.mixer:
- 44100 Hz sample rate
- Low latency buffer
- Supports multiple simultaneous notes

## 🚀 Run Project

pip install -r requirements.txt
python generate_sounds.py
python main.py

## 🔮 Future Improvements

- Full piano octave expansion
- Chord detection
- Volume control via hand distance
- MIDI output support
- Recording feature
- Visual piano UI

## 📦 Dependencies

OpenCV  
MediaPipe  
NumPy  
Pygame  

## 📄 License

MIT License — free to use and modify.
