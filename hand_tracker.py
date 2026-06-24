"""
hand_tracker.py
---------------
Handles webcam initialization, MediaPipe hand detection,
landmark extraction, landmark drawing, and hand identification (left/right).
"""

import cv2
import mediapipe as mp
import numpy as np


class HandTracker:
    """
    Manages real-time hand tracking using MediaPipe Hands.

    Responsibilities:
    - Initialize and release the webcam
    - Configure MediaPipe Hands solution
    - Process frames to detect hands
    - Extract normalized and pixel-space landmarks
    - Draw landmarks and connections with custom styling
    - Identify whether a detected hand is left or right
    """

    # ── MediaPipe drawing style constants ──────────────────────────────────
    # Blue dots for landmark points (BGR: (255, 0, 0))
    LANDMARK_COLOR   = (255, 0, 0)    # Blue in BGR
    CONNECTION_COLOR = (0, 255, 0)    # Green connections
    LANDMARK_RADIUS  = 6
    CONNECTION_THICKNESS = 2

    def __init__(
        self,
        camera_index: int = 0,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.7,
    ) -> None:
        """
        Initialize HandTracker.

        Args:
            camera_index: Index of the webcam device (default 0).
            max_num_hands: Maximum number of hands to detect simultaneously.
            min_detection_confidence: Confidence threshold for initial detection.
            min_tracking_confidence: Confidence threshold for frame-to-frame tracking.
        """
        # ── Webcam setup ───────────────────────────────────────────────────
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open webcam at index {camera_index}. "
                "Please check your camera connection."
            )

        # Optional: request a reasonable resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # ── MediaPipe Hands solution ───────────────────────────────────────
        self.mp_hands    = mp.solutions.hands
        self.mp_drawing  = mp.solutions.drawing_utils
        self.mp_draw_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,           # Real-time video mode
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        # ── Custom drawing specs ───────────────────────────────────────────
        # Override default MediaPipe colours with blue landmarks
        self.landmark_drawing_spec = self.mp_drawing.DrawingSpec(
            color=self.LANDMARK_COLOR,
            thickness=self.LANDMARK_RADIUS,
            circle_radius=self.LANDMARK_RADIUS,
        )
        self.connection_drawing_spec = self.mp_drawing.DrawingSpec(
            color=self.CONNECTION_COLOR,
            thickness=self.CONNECTION_THICKNESS,
        )

        # Store the most recent results from MediaPipe
        self.results = None

    # ──────────────────────────────────────────────────────────────────────
    # Frame capture
    # ──────────────────────────────────────────────────────────────────────

    def read_frame(self):
        """
        Capture a single frame from the webcam.

        Returns:
            tuple[bool, np.ndarray | None]: (success, frame_in_BGR)
        """
        ret, frame = self.cap.read()
        if not ret:
            return False, None

        # Flip horizontally for a mirror-like (selfie) view
        frame = cv2.flip(frame, 1)
        return True, frame

    # ──────────────────────────────────────────────────────────────────────
    # Hand detection
    # ──────────────────────────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray):
        """
        Run MediaPipe hand detection on a BGR frame.

        MediaPipe requires RGB input, so we convert before processing
        and store the results internally for later use.

        Args:
            frame: BGR image from OpenCV.

        Returns:
            The raw MediaPipe results object (may contain 0-N hands).
        """
        # Convert BGR → RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Mark as non-writeable to improve performance (avoids a copy)
        rgb_frame.flags.writeable = False
        self.results = self.hands.process(rgb_frame)
        rgb_frame.flags.writeable = True

        return self.results

    # ──────────────────────────────────────────────────────────────────────
    # Landmark extraction
    # ──────────────────────────────────────────────────────────────────────

    def get_landmark_list(self, frame: np.ndarray, hand_index: int) -> list[tuple[int, int]]:
        """
        Convert normalized MediaPipe landmarks to pixel coordinates.

        MediaPipe stores landmarks as values in [0, 1] relative to the
        frame dimensions. Multiplying by width/height gives us pixel positions.

        Args:
            frame: The current BGR frame (used to obtain dimensions).
            hand_index: Which detected hand to extract (0-based).

        Returns:
            List of 21 (x, y) pixel tuples, one per landmark.
            Returns an empty list if no hands are detected.
        """
        landmark_list: list[tuple[int, int]] = []

        if not self.results or not self.results.multi_hand_landmarks:
            return landmark_list

        h, w, _ = frame.shape
        hand_landmarks = self.results.multi_hand_landmarks[hand_index]

        for lm in hand_landmarks.landmark:
            # Convert normalized [0,1] coordinates to pixel space
            cx = int(lm.x * w)
            cy = int(lm.y * h)
            landmark_list.append((cx, cy))

        return landmark_list

    def get_all_hands_data(self, frame: np.ndarray) -> list[dict]:
        """
        Build a structured list of hand data for every detected hand.

        Each entry contains:
            - 'label'     : 'Left' or 'Right' (from MediaPipe classification)
            - 'landmarks' : list of 21 (x, y) pixel tuples
            - 'raw'       : raw MediaPipe hand_landmarks object (for drawing)

        Args:
            frame: The current BGR frame.

        Returns:
            List of hand-data dicts (empty if no hands detected).
        """
        hands_data: list[dict] = []

        if not self.results or not self.results.multi_hand_landmarks:
            return hands_data

        for i, hand_landmarks in enumerate(self.results.multi_hand_landmarks):
            # MediaPipe classifies each hand as Left or Right.
            # Because we flipped the frame, the labels are already correct
            # from the user's perspective.
            label = self.results.multi_handedness[i].classification[0].label

            landmarks = self.get_landmark_list(frame, i)

            hands_data.append({
                "label":     label,      # 'Left' or 'Right'
                "landmarks": landmarks,  # [(x,y), ...] × 21
                "raw":       hand_landmarks,  # For mp_drawing
            })

        return hands_data

    # ──────────────────────────────────────────────────────────────────────
    # Drawing
    # ──────────────────────────────────────────────────────────────────────

    def draw_landmarks(self, frame: np.ndarray, hand_raw) -> None:
        """
        Draw all 21 landmark dots and their connections onto the frame.

        Uses the custom blue landmark style and green connections.

        Args:
            frame: BGR frame to draw on (modified in-place).
            hand_raw: The raw MediaPipe NormalizedLandmarkList for one hand.
        """
        self.mp_drawing.draw_landmarks(
            frame,
            hand_raw,
            self.mp_hands.HAND_CONNECTIONS,
            self.landmark_drawing_spec,    # Dot style (blue)
            self.connection_drawing_spec,  # Line style (green)
        )

    # ──────────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────────

    def release(self) -> None:
        """Release the webcam and close the MediaPipe graph."""
        self.cap.release()
        self.hands.close()
