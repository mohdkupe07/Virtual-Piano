# 🎹 Hand Gesture Controlled Virtual Piano

A real-time virtual piano controlled entirely using hand gestures via webcam.  
Built with Python 3.11+, OpenCV, MediaPipe, NumPy, and Pygame.

---

# 📋 Project Overview

This project uses computer vision to detect hands using webcam and maps finger gestures to piano notes.

Just raise your fingers to play notes — no keyboard required.

Finger Mapping:
Thumb = C  
Index = D  
Middle = E  
Ring = F  
Pinky = G  

Pinch gesture (Thumb + Index) is also detected.

---

# 🗂 Folder Structure

VirtualPiano/
│
├── main.py                 # Entry point
├── hand_tracker.py        # MediaPipe hand tracking
├── gesture_detector.py    # Finger + pinch detection
├── piano_player.py        # Sound playback
├── generate_sounds.py     # Create .wav files
├── requirements.txt       # Dependencies
├── README.md
│
└── sounds/
    ├── C.wav
    ├── D.wav
    ├── E.wav
    ├── F.wav
    └── G.wav

---

# ⚙️ Installation

## 1 Clone project
git clone <repo-url>
cd VirtualPiano

## 2 Create virtual environment
python -m venv venv

Windows:
venv\Scripts\activate

Mac/Linux:
source venv/bin/activate

## 3 Install dependencies
pip install -r requirements.txt

OR
pip install opencv-python mediapipe numpy pygame

## 4 Generate sounds
python generate_sounds.py

## 5 Run project
python main.py

---

# 🎮 Controls

Thumb  → C  
Index  → D  
Middle → E  
Ring   → F  
Pinky  → G  

Pinch = Thumb + Index  
Quit = Q or ESC  

---

# 🖥️ Working Display

FPS shown  
Active note shown  
Finger states shown  
Live webcam feed with landmarks  

---

# 🔬 How It Works

MediaPipe detects 21 hand landmarks.

Each finger is checked:

Index/Middle/Ring/Pinky:
tip.y < pip.y → finger UP

Thumb:
Right hand → thumb_tip.x < ip.x  
Left hand  → thumb_tip.x > ip.x  

---

# 🤏 Pinch Detection

distance = sqrt((x4-x8)^2 + (y4-y8)^2)

If distance < threshold → pinch detected

Threshold = 40 pixels

---

# 🔁 Debounce Logic

Prevents repeated triggers every frame.

Only triggers on:
DOWN → UP transition

---

# 🎵 Sound System

Uses pygame.mixer

- 44100 Hz audio
- Low latency buffer
- Multiple notes supported

---

# 🚀 Run Project

pip install -r requirements.txt
python generate_sounds.py
python main.py

---

# 🔭 Future Improvements

- Full piano keyboard (2 octaves)
- Chord detection
- Volume control via hand distance
- MIDI support
- Recording feature
- Visual piano UI

---

# 📦 Dependencies

opencv-python  
mediapipe  
numpy  
pygame  

---

# 📄 License

MIT License-->free to use, modify, and distribute.
