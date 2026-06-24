# 🎹 Hand Gesture Controlled Virtual Piano

A real-time virtual piano controlled entirely by hand gestures using your webcam.  
Built with **Python 3.11+**, **OpenCV**, **MediaPipe**, **NumPy**, and **Pygame**.

---

## 📋 Project Overview

This application uses computer vision to detect your hands via webcam and maps
finger gestures to piano notes. Simply raise a finger to play a note — no physical
keyboard required.

| Finger  | Note |
|---------|------|
| Thumb   | C    |
| Index   | D    |
| Middle  | E    |
| Ring    | F    |
| Pinky   | G    |

A **pinch** gesture (thumb tip meeting index tip) is also detected and displayed on screen.

---

## 🗂 Folder Structure

```
VirtualPiano/
│
├── main.py               ← Application entry point
├── hand_tracker.py       ← Webcam + MediaPipe landmark detection
├── gesture_detector.py   ← Finger counting, pinch, debounce, note selection
├── piano_player.py       ← pygame audio loading and playback
├── generate_sounds.py    ← Utility: synthesise piano .wav files (run once)
├── requirements.txt      ← Python dependencies
├── README.md             ← This file
│
└── sounds/
    ├── C.wav
    ├── D.wav
    ├── E.wav
    ├── F.wav
    └── G.wav
```

---

## ⚙️ Installation

### 1 — Clone / download the project

```bash
git clone <repo-url>
cd VirtualPiano
```

### 2 — Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install opencv-python mediapipe numpy pygame
```

### 4 — Generate piano sound files

If you do not have your own `.wav` files, run the bundled synthesiser **once**:

```bash
python generate_sounds.py
```

This creates `sounds/C.wav` through `sounds/G.wav` using harmonic synthesis.
You can replace these files with any 44100 Hz mono or stereo `.wav` files you prefer.

### 5 — Run the application

```bash
python main.py
```

---

## 🎮 Controls

| Action              | Gesture / Key           |
|---------------------|-------------------------|
| Play note C         | Raise **Thumb**         |
| Play note D         | Raise **Index finger**  |
| Play note E         | Raise **Middle finger** |
| Play note F         | Raise **Ring finger**   |
| Play note G         | Raise **Pinky**         |
| Pinch (visual only) | Bring Thumb + Index together |
| Quit                | Press **Q** or **ESC** |

> **Tip:** You can use both hands simultaneously. The piano will trigger notes
> from whichever hand raises a finger first in a given frame.

---

## 🖥️ On-Screen Display

```
┌─────────────────────────────────────────────────┐
│ FPS: 30              Playing: D                 │
│                                                 │
│ Right Fingers: 1                                │
│ Left Fingers:  0                                │
│                                                 │
│ Right Pinched: 0                                │
│ Left Pinched:  1                                │
│                                                 │
│      [live webcam feed with blue dots]          │
│                                                 │
│ Thumb=C  Index=D  Middle=E  Ring=F  Pinky=G     │
│ Press Q or ESC to quit                          │
└─────────────────────────────────────────────────┘
```

---

## 🔬 How Gesture Recognition Works

### MediaPipe Hand Landmarks

MediaPipe detects **21 landmarks** per hand, each identified by a numeric index:

```
       4                      ← Thumb Tip
      /
   3 /
    /
  2
  |
  1
  |
  0  ← Wrist
```

Full layout:

```
Wrist (0)
Thumb:   CMC(1) MCP(2) IP(3)   Tip(4)
Index:   MCP(5) PIP(6) DIP(7)  Tip(8)
Middle:  MCP(9) PIP(10) DIP(11) Tip(12)
Ring:    MCP(13) PIP(14) DIP(15) Tip(16)
Pinky:   MCP(17) PIP(18) DIP(19) Tip(20)
```

Landmarks are returned as normalised coordinates `(x, y)` in `[0, 1]`,
which we convert to pixel positions by multiplying by frame width/height.

---

## ☝️ How Finger Counting Works

### Four fingers (Index → Pinky)

Each finger has a **Tip** and a **PIP** (middle knuckle) landmark.

- In image space, **y increases downward**.
- When a finger is raised, its tip moves **up** → smaller y value.
- Therefore: **finger is UP when `tip.y < pip.y`**

```python
# Index finger example
states["Index"] = landmarks[INDEX_TIP][1] < landmarks[INDEX_PIP][1]
```

### Thumb

The thumb moves **laterally**, not vertically, so we compare **x-coordinates**:

- **Right hand** (mirrored/selfie frame): extended thumb tip is to the **left** → `tip.x < ip.x`
- **Left hand**: extended thumb tip is to the **right** → `tip.x > ip.x`

```python
if label == "Right":
    states["Thumb"] = thumb_tip_x < thumb_ip_x
else:
    states["Thumb"] = thumb_tip_x > thumb_ip_x
```

---

## 🤏 How Pinch Detection Works

A **pinch** is detected when the **Euclidean distance** between:

- **Landmark 4** — Thumb Tip
- **Landmark 8** — Index Tip

falls below a pixel threshold (default: **40 px** for a 1280×720 frame).

```
distance = √( (x4-x8)² + (y4-y8)² )
pinched  = distance < PINCH_THRESHOLD
```

The threshold can be adjusted in `gesture_detector.py`:

```python
PINCH_THRESHOLD = 40  # pixels
```

---

## 🔁 How Debounce Logic Works

Without debounce, a raised finger would trigger its note **every frame** (~30×/sec).

The debounce system detects only the **rising edge** — the moment a finger
transitions from **down → up**:

```
Frame N-1:  Index = DOWN (False)
Frame N:    Index = UP   (True)   ← TRIGGER NOTE HERE
Frame N+1:  Index = UP   (True)   ← Ignored
Frame N+2:  Index = UP   (True)   ← Ignored
Frame N+3:  Index = DOWN (False)
Frame N+4:  Index = UP   (True)   ← TRIGGER AGAIN (new gesture)
```

Implementation in `gesture_detector.py`:

```python
if is_up and not was_up:      # Rising edge detected
    triggered_note = FINGER_NOTE_MAP[finger_name]
    break
```

Previous states are stored per-hand in `self.prev_finger_states` and
updated at the end of every frame.

---

## 🎵 How Sound Playback Works

1. **pygame.mixer** is initialised with low-latency settings:
   - Sample rate: 44100 Hz
   - Buffer size: 512 samples (~11 ms latency)
   - 8 simultaneous channels

2. Each `.wav` file is loaded into a `pygame.mixer.Sound` object at startup.

3. When `play_note(note)` is called, the corresponding Sound plays immediately
   on any free channel.

4. Multiple notes can overlap naturally (e.g., two fingers raised simultaneously
   on different hands within the same frame window).

---

## 🚀 Running the Project (Step-by-Step)

```bash
# Step 1: Install dependencies
pip install -r requirements.txt

# Step 2: Generate sound files (only needed once)
python generate_sounds.py

# Step 3: Launch the piano
python main.py
```

The webcam window opens automatically. Hold your hand(s) in front of the camera
and raise fingers to play notes.

---

## 🔭 Future Improvements

| Feature                      | Description                                                         |
|------------------------------|---------------------------------------------------------------------|
| Full octave range            | Map all 10 fingers across two hands to a full 10-note scale        |
| Velocity sensitivity         | Map distance of finger raise to note volume                         |
| Chord detection              | Recognise multiple simultaneous fingers as chords                   |
| Visual piano keyboard        | Render a piano keyboard overlay and highlight active keys           |
| Recording & playback         | Record played note sequences and replay them                        |
| MIDI output                  | Send MIDI events to a DAW or synthesiser                            |
| Custom sound packs           | UI to swap between different instrument .wav libraries              |
| Pinch-to-sustain             | Hold a pinch to sustain the last played note                        |
| Hand distance dynamics       | Use z-depth from MediaPipe to add reverb or pitch bend              |
| Settings panel               | On-screen sliders for threshold, volume, octave shift               |

---

## 📦 Dependencies

| Package          | Version  | Purpose                        |
|------------------|----------|--------------------------------|
| opencv-python    | ≥ 4.8.0  | Webcam capture & image display |
| mediapipe        | ≥ 0.10.0 | Hand landmark detection        |
| numpy            | ≥ 1.24.0 | Numerical operations           |
| pygame           | ≥ 2.5.0  | Audio playback                 |

---

## 📄 License

MIT License — free to use, modify, and distribute.
