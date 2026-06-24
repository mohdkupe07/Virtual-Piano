"""
gesture_detector.py
-------------------
Handles all gesture logic:
- Finger counting (which fingers are raised)
- Pinch detection (thumb tip close to index tip)
- Debounce logic (prevent repeated note triggers on sustained gestures)
- Note selection (map raised fingers to piano notes)
"""

import math


class GestureDetector:
    """
    Analyses hand landmark positions to recognise gestures.

    MediaPipe landmark numbering (relevant ones):
        0  - Wrist
        1  - Thumb CMC       2  - Thumb MCP
        3  - Thumb IP        4  - Thumb Tip   ← used for pinch & thumb-up
        5  - Index MCP       6  - Index PIP
        7  - Index DIP       8  - Index Tip   ← used for pinch & index-up
        9  - Middle MCP      10 - Middle PIP
        11 - Middle DIP      12 - Middle Tip
        13 - Ring MCP        14 - Ring PIP
        15 - Ring DIP        16 - Ring Tip
        17 - Pinky MCP       18 - Pinky PIP
        19 - Pinky DIP       20 - Pinky Tip

    Finger-to-note mapping:
        Thumb  (4)  → C
        Index  (8)  → D
        Middle (12) → E
        Ring   (16) → F
        Pinky  (20) → G
    """

    # ── Landmark indices ───────────────────────────────────────────────────
    WRIST           = 0
    THUMB_CMC       = 1
    THUMB_MCP       = 2
    THUMB_IP        = 3
    THUMB_TIP       = 4

    INDEX_MCP       = 5
    INDEX_PIP       = 6
    INDEX_DIP       = 7
    INDEX_TIP       = 8

    MIDDLE_MCP      = 9
    MIDDLE_PIP      = 10
    MIDDLE_DIP      = 11
    MIDDLE_TIP      = 12

    RING_MCP        = 13
    RING_PIP        = 14
    RING_DIP        = 15
    RING_TIP        = 16

    PINKY_MCP       = 17
    PINKY_PIP       = 18
    PINKY_DIP       = 19
    PINKY_TIP       = 20

    # ── Note mapping: finger name → MIDI-style note label ─────────────────
    FINGER_NOTE_MAP = {
        "Thumb":  "C",
        "Index":  "D",
        "Middle": "E",
        "Ring":   "F",
        "Pinky":  "G",
    }

    # ── Pinch threshold (Euclidean distance in pixels) ─────────────────────
    # Calibrated for a 1280×720 frame; adjust if you use a different resolution
    PINCH_THRESHOLD = 40

    def __init__(self) -> None:
        """
        Initialise the detector with per-hand debounce state.

        prev_finger_states stores the finger-up/down state from the
        previous frame for each hand label ('Left' / 'Right').
        This allows us to detect the DOWN→UP transition edge.
        """
        # {hand_label: {"Thumb": bool, "Index": bool, ...}}
        self.prev_finger_states: dict[str, dict[str, bool]] = {
            "Left":  {f: False for f in self.FINGER_NOTE_MAP},
            "Right": {f: False for f in self.FINGER_NOTE_MAP},
        }

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def count_fingers(self, landmarks: list[tuple[int, int]], label: str) -> int:
        """
        Count how many fingers are currently raised.

        Args:
            landmarks: 21 (x, y) pixel tuples from HandTracker.
            label: 'Left' or 'Right' hand label.

        Returns:
            Integer count of raised fingers (0–5).
        """
        if not landmarks:
            return 0

        finger_states = self._get_finger_states(landmarks, label)
        return sum(finger_states.values())

    def is_pinched(self, landmarks: list[tuple[int, int]]) -> bool:
        """
        Detect a pinch gesture between thumb tip and index finger tip.

        A pinch is active when the Euclidean distance between landmark 4
        (Thumb Tip) and landmark 8 (Index Tip) is below PINCH_THRESHOLD.

        Args:
            landmarks: 21 (x, y) pixel tuples.

        Returns:
            True if pinching, False otherwise.
        """
        if not landmarks or len(landmarks) < 9:
            return False

        thumb_tip = landmarks[self.THUMB_TIP]
        index_tip = landmarks[self.INDEX_TIP]

        distance = self._euclidean(thumb_tip, index_tip)
        return distance < self.PINCH_THRESHOLD

    def get_active_note(
        self,
        landmarks: list[tuple[int, int]],
        label: str,
    ) -> str | None:
        """
        Return the note that should be triggered this frame, if any.

        Uses debounce logic: a note fires only on the rising edge of a
        finger becoming raised (DOWN→UP transition), not while it stays up.

        Args:
            landmarks: 21 (x, y) pixel tuples.
            label: 'Left' or 'Right' (used to maintain separate debounce state).

        Returns:
            A note string ('C','D','E','F','G') or None.
        """
        if not landmarks:
            # If no landmarks, reset state for this hand so next appearance
            # triggers fresh notes (avoids stuck-note bugs).
            self.prev_finger_states[label] = {f: False for f in self.FINGER_NOTE_MAP}
            return None

        current_states = self._get_finger_states(landmarks, label)
        triggered_note: str | None = None

        for finger_name, is_up in current_states.items():
            was_up = self.prev_finger_states[label][finger_name]

            # Rising edge: finger just moved from down → up
            if is_up and not was_up:
                triggered_note = self.FINGER_NOTE_MAP[finger_name]
                # We trigger only the first (priority: Thumb > Index > … > Pinky)
                # Break so multiple simultaneous rising edges only fire once.
                break

        # Update debounce state for next frame
        self.prev_finger_states[label] = current_states
        return triggered_note

    def get_finger_states(
        self,
        landmarks: list[tuple[int, int]],
        label: str,
    ) -> dict[str, bool]:
        """
        Public wrapper to expose the current finger states dictionary.

        Args:
            landmarks: 21 (x, y) pixel tuples.
            label: 'Left' or 'Right'.

        Returns:
            Dict mapping finger name to True (up) / False (down).
        """
        if not landmarks:
            return {f: False for f in self.FINGER_NOTE_MAP}
        return self._get_finger_states(landmarks, label)

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _get_finger_states(
        self,
        landmarks: list[tuple[int, int]],
        label: str,
    ) -> dict[str, bool]:
        """
        Determine the up/down state of each finger.

        Logic overview
        ──────────────
        Four fingers (Index, Middle, Ring, Pinky):
            A finger is "up" when its TIP landmark has a LOWER y-coordinate
            than its PIP (second knuckle) landmark.
            (In image space, y increases downward, so a raised finger tip
            has a smaller y value than the knuckle below it.)

        Thumb:
            The thumb moves laterally rather than vertically, so we compare
            x-coordinates instead.
            - Right hand: thumb tip is to the LEFT of the IP joint when extended
              (i.e., tip_x < ip_x in a mirrored/selfie frame).
            - Left hand:  thumb tip is to the RIGHT (tip_x > ip_x).

        Args:
            landmarks: 21 (x, y) pixel tuples.
            label: 'Left' or 'Right'.

        Returns:
            {'Thumb': bool, 'Index': bool, 'Middle': bool, 'Ring': bool, 'Pinky': bool}
        """
        states: dict[str, bool] = {}

        # ── Thumb ──────────────────────────────────────────────────────────
        thumb_tip_x  = landmarks[self.THUMB_TIP][0]
        thumb_ip_x   = landmarks[self.THUMB_IP][0]

        if label == "Right":
            # Mirrored frame: right hand thumb extends to the LEFT
            states["Thumb"] = thumb_tip_x < thumb_ip_x
        else:
            # Left hand thumb extends to the RIGHT
            states["Thumb"] = thumb_tip_x > thumb_ip_x

        # ── Index ──────────────────────────────────────────────────────────
        states["Index"] = (
            landmarks[self.INDEX_TIP][1] < landmarks[self.INDEX_PIP][1]
        )

        # ── Middle ─────────────────────────────────────────────────────────
        states["Middle"] = (
            landmarks[self.MIDDLE_TIP][1] < landmarks[self.MIDDLE_PIP][1]
        )

        # ── Ring ───────────────────────────────────────────────────────────
        states["Ring"] = (
            landmarks[self.RING_TIP][1] < landmarks[self.RING_PIP][1]
        )

        # ── Pinky ──────────────────────────────────────────────────────────
        states["Pinky"] = (
            landmarks[self.PINKY_TIP][1] < landmarks[self.PINKY_PIP][1]
        )

        return states

    @staticmethod
    def _euclidean(p1: tuple[int, int], p2: tuple[int, int]) -> float:
        """
        Compute the Euclidean distance between two 2-D points.

        Args:
            p1: (x1, y1)
            p2: (x2, y2)

        Returns:
            Float distance in the same units as the input coordinates (pixels).
        """
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
