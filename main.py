"""
main.py
-------
Hand Gesture Controlled Virtual Piano
======================================
Entry point that ties together HandTracker, GestureDetector, and PianoPlayer
into a real-time OpenCV desktop application.

Run:
    python main.py

Controls:
    Q or ESC  →  Quit the application
"""

import sys
import time

import cv2
import numpy as np

from hand_tracker import HandTracker
from gesture_detector import GestureDetector
from piano_player import PianoPlayer


# ════════════════════════════════════════════════════════════════════════════
# Overlay drawing helpers
# ════════════════════════════════════════════════════════════════════════════

def draw_text(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    font_scale: float = 0.75,
    color: tuple[int, int, int] = (255, 255, 255),
    thickness: int = 2,
    background: bool = True,
) -> None:
    """
    Render antialiased text with an optional dark background pill.

    Having a semi-transparent background behind white text ensures the
    overlay remains readable regardless of what colour the hand/background is.

    Args:
        frame:      BGR image to draw on (modified in-place).
        text:       String to render.
        position:   (x, y) pixel coordinate of the text bottom-left origin.
        font_scale: Size multiplier for the font.
        color:      BGR text colour.
        thickness:  Stroke weight in pixels.
        background: If True, draw a filled black rectangle behind the text.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    if background:
        pad = 6
        x, y = position
        cv2.rectangle(
            frame,
            (x - pad, y - th - pad),
            (x + tw + pad, y + baseline + pad),
            (0, 0, 0),       # Black fill
            cv2.FILLED,
        )

    cv2.putText(frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)


def draw_overlay(
    frame: np.ndarray,
    fps: float,
    playing_note: str | None,
    right_fingers: int,
    left_fingers: int,
    right_pinched: bool,
    left_pinched: bool,
) -> None:
    """
    Render the full HUD (heads-up display) on the frame.

    Layout:
        Top-left:    FPS counter
        Top-center:  Currently playing note
        Left column: Per-hand finger count and pinch status

    Args:
        frame:         BGR frame to annotate.
        fps:           Calculated frames per second.
        playing_note:  Last triggered note (or None).
        right_fingers: Count of raised fingers on right hand.
        left_fingers:  Count of raised fingers on left hand.
        right_pinched: Whether the right hand is pinching.
        left_pinched:  Whether the left hand is pinching.
    """
    h, w = frame.shape[:2]

    # ── Top-left: FPS ────────────────────────────────────────────────────
    draw_text(frame, f"FPS: {fps:.1f}", (20, 40), font_scale=0.8, color=(0, 255, 0))

    # ── Top-center: Playing note ─────────────────────────────────────────
    note_label = playing_note if playing_note else "-"
    note_text  = f"Playing: {note_label}"
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness  = 2
    (tw, _), _ = cv2.getTextSize(note_text, font, font_scale, thickness)
    note_x = (w - tw) // 2
    draw_text(
        frame, note_text, (note_x, 45),
        font_scale=font_scale,
        color=(0, 255, 255),  # Cyan
        thickness=thickness,
    )

    # ── Left column: Finger counts and pinch status ───────────────────────
    y_start  = 110
    y_step   = 32
    col_x    = 20
    col_color = (200, 200, 255)  # Light blue-white

    draw_text(frame, f"Right Fingers: {right_fingers}", (col_x, y_start),
              font_scale=0.7, color=col_color)
    draw_text(frame, f"Left Fingers:  {left_fingers}",  (col_x, y_start + y_step),
              font_scale=0.7, color=col_color)

    # Blank line spacer
    pinch_y = y_start + y_step * 2 + 16
    draw_text(frame, f"Right Pinched: {int(right_pinched)}", (col_x, pinch_y),
              font_scale=0.7, color=(100, 255, 100))
    draw_text(frame, f"Left Pinched:  {int(left_pinched)}",  (col_x, pinch_y + y_step),
              font_scale=0.7, color=(100, 255, 100))

    # ── Bottom: Key mapping legend ────────────────────────────────────────
    legend_lines = [
        "Thumb=C  Index=D  Middle=E  Ring=F  Pinky=G",
        "Press Q or ESC to quit",
    ]
    for i, line in enumerate(legend_lines):
        draw_text(
            frame, line,
            (20, h - 20 - (len(legend_lines) - 1 - i) * 28),
            font_scale=0.55,
            color=(180, 180, 180),
        )


# ════════════════════════════════════════════════════════════════════════════
# Main application loop
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Application entry point.

    Initialises all subsystems, then runs the main capture-process-display
    loop until the user presses Q / ESC or closes the window.
    """

    print("=" * 60)
    print("  Hand Gesture Controlled Virtual Piano")
    print("=" * 60)
    print("Starting up…\n")

    # ── Initialise subsystems ────────────────────────────────────────────
    try:
        tracker  = HandTracker(camera_index=0)
        print("[Main] HandTracker initialised.")
    except RuntimeError as exc:
        print(f"[Main] FATAL: {exc}")
        sys.exit(1)

    detector = GestureDetector()
    print("[Main] GestureDetector initialised.")

    player = PianoPlayer(sounds_dir="sounds")
    print("[Main] PianoPlayer initialised.\n")

    # ── Window setup ─────────────────────────────────────────────────────
    window_name = "Virtual Piano – Hand Gesture Control"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    # ── State variables ──────────────────────────────────────────────────
    playing_note: str | None = None   # Last note triggered (shown on HUD)
    note_display_frames = 0           # Countdown for how long to show the note
    NOTE_DISPLAY_DURATION = 15        # Show note label for N frames

    # ── FPS tracking ─────────────────────────────────────────────────────
    fps         = 0.0
    frame_count = 0
    fps_start   = time.time()
    FPS_UPDATE_INTERVAL = 0.5        # Recalculate FPS every 0.5 seconds

    print("[Main] Entering main loop. Press Q or ESC to quit.")
    print()

    # ════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ════════════════════════════════════════════════════════════════════
    while True:

        # ── 1. Capture frame ─────────────────────────────────────────────
        success, frame = tracker.read_frame()
        if not success or frame is None:
            print("[Main] WARNING: Failed to read frame. Retrying…")
            continue

        # ── 2. Run MediaPipe hand detection ──────────────────────────────
        tracker.process_frame(frame)

        # ── 3. Gather structured hand data ───────────────────────────────
        all_hands = tracker.get_all_hands_data(frame)

        # ── 4. Per-hand defaults (shown when no hands detected) ───────────
        right_fingers  = 0
        left_fingers   = 0
        right_pinched  = False
        left_pinched   = False

        # ── 5. Process each detected hand ────────────────────────────────
        for hand in all_hands:
            label     = hand["label"]      # 'Left' or 'Right'
            landmarks = hand["landmarks"]  # [(x,y), ...] × 21
            raw       = hand["raw"]        # For mp_drawing

            # 5a. Draw landmarks + connections onto the frame
            tracker.draw_landmarks(frame, raw)

            # 5b. Count fingers
            count = detector.count_fingers(landmarks, label)

            # 5c. Check pinch
            pinched = detector.is_pinched(landmarks)

            # 5d. Debounce-aware note detection
            triggered = detector.get_active_note(landmarks, label)
            if triggered:
                player.play_note(triggered)
                playing_note      = triggered
                note_display_frames = NOTE_DISPLAY_DURATION

            # 5e. Assign per-hand stats to display variables
            if label == "Right":
                right_fingers = count
                right_pinched = pinched
            else:
                left_fingers  = count
                left_pinched  = pinched

        # ── 6. Tick down the note-display timer ──────────────────────────
        if note_display_frames > 0:
            note_display_frames -= 1
        else:
            playing_note = None

        # ── 7. FPS calculation ────────────────────────────────────────────
        frame_count += 1
        elapsed = time.time() - fps_start
        if elapsed >= FPS_UPDATE_INTERVAL:
            fps         = frame_count / elapsed
            frame_count = 0
            fps_start   = time.time()

        # ── 8. Draw HUD overlay ───────────────────────────────────────────
        draw_overlay(
            frame,
            fps,
            playing_note,
            right_fingers,
            left_fingers,
            right_pinched,
            left_pinched,
        )

        # ── 9. Display frame ──────────────────────────────────────────────
        cv2.imshow(window_name, frame)

        # ── 10. Handle keyboard input ─────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):  # Q or ESC
            print("[Main] Quit signal received.")
            break

        # Also quit if user closes the window via the OS close button
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            print("[Main] Window closed by user.")
            break

    # ── Cleanup ──────────────────────────────────────────────────────────
    print("[Main] Releasing resources…")
    tracker.release()
    player.quit()
    cv2.destroyAllWindows()
    print("[Main] Done. Goodbye!")


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
