"""
piano_player.py
---------------
Handles all audio functionality:
- Initialize pygame mixer
- Load .wav files from the sounds/ directory
- Play notes on demand without overlapping
- Graceful handling of missing audio files
"""

import os
import pygame
try:
    import winsound
    _HAS_WINSOUND = True
except Exception:
    _HAS_WINSOUND = False


class PianoPlayer:
    """
    Manages piano note playback using pygame.mixer.

    Each note is loaded into a pygame.mixer.Sound object.
    When play_note() is called, the corresponding sound is played
    immediately. pygame handles hardware-level mixing so simultaneous
    notes do not clip or block each other.

    Folder structure expected:
        <sounds_dir>/
            C.wav
            D.wav
            E.wav
            F.wav
            G.wav

    If a .wav file is missing, that note is silently skipped and a
    warning is printed so the rest of the piano still works.
    """

    # Notes to load, in scale order
    NOTES = ["C", "D", "E", "F", "G"]

    def __init__(self, sounds_dir: str = "sounds") -> None:
        """
        Initialise pygame.mixer and load all audio assets.

        Args:
            sounds_dir: Relative or absolute path to the folder
                        containing C.wav … G.wav.
        """
        self.sounds_dir = sounds_dir
        self.sounds: dict[str, pygame.mixer.Sound | None] = {}
        self.file_paths: dict[str, str] = {}

        self._init_mixer()
        self.load_notes()

    # ──────────────────────────────────────────────────────────────────────
    # Initialisation
    # ──────────────────────────────────────────────────────────────────────

    def _init_mixer(self) -> None:
        """
        Boot the pygame audio subsystem.

        Settings:
            frequency  = 44100 Hz  (CD quality)
            size       = -16       (signed 16-bit samples)
            channels   = 2         (stereo)
            buffer     = 512       (small buffer → low latency ~11 ms)

        A small buffer is critical for a real-time instrument; larger
        buffers introduce audible lag between gesture and sound.
        """
        pygame.mixer.pre_init(
            frequency=44100,
            size=-16,
            channels=2,
            buffer=512,
        )
        pygame.mixer.init()

        # Allow up to 8 simultaneous channels so rapid playing doesn't cut off
        pygame.mixer.set_num_channels(8)

    # ──────────────────────────────────────────────────────────────────────
    # Asset loading
    # ──────────────────────────────────────────────────────────────────────

    def load_notes(self) -> None:
        """
        Load each note's .wav file into a pygame Sound object.

        Missing files are logged with a clear warning but do NOT crash
        the application. The corresponding note will simply be skipped
        during playback.
        """
        for note in self.NOTES:
            file_path = os.path.join(self.sounds_dir, f"{note}.wav")

            if not os.path.isfile(file_path):
                print(
                    f"[PianoPlayer] WARNING: Audio file not found: '{file_path}'. "
                    f"Note '{note}' will be silent."
                )
                self.sounds[note] = None
                self.file_paths[note] = file_path
                continue

            try:
                self.sounds[note] = pygame.mixer.Sound(file_path)
                self.file_paths[note] = file_path
                # Normalise volume to 80% to leave headroom for mixing
                self.sounds[note].set_volume(0.80)
                print(f"[PianoPlayer] Loaded: {file_path}")
            except pygame.error as exc:
                print(
                    f"[PianoPlayer] ERROR loading '{file_path}': {exc}. "
                    f"Note '{note}' will be silent."
                )
                self.sounds[note] = None

    # ──────────────────────────────────────────────────────────────────────
    # Playback
    # ──────────────────────────────────────────────────────────────────────

    def play_note(self, note: str) -> bool:
        """
        Play the given note.

        The sound is played on any available free channel.  If all 8
        channels are busy, pygame automatically steals the oldest one,
        so notes never become permanently stuck.

        Args:
            note: One of 'C', 'D', 'E', 'F', 'G'.

        Returns:
            True if the note was played successfully, False otherwise.
        """
        sound = self.sounds.get(note)
        file_path = self.file_paths.get(note)

        # Try pygame mixer first
        if sound is not None:
            try:
                sound.play()
                return True
            except Exception as exc:
                print(f"[PianoPlayer] ERROR playing note '{note}' with pygame: {exc}")

        # Fallback: on Windows use winsound to play the file asynchronously
        if _HAS_WINSOUND and file_path and os.path.isfile(file_path):
            try:
                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                print(f"[PianoPlayer] Playing '{note}' via winsound fallback.")
                return True
            except Exception as exc:
                print(f"[PianoPlayer] ERROR playing note '{note}' with winsound: {exc}")

        # Nothing worked
        return False

    # ──────────────────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────────────────

    def is_note_loaded(self, note: str) -> bool:
        """Return True if the given note has a valid Sound object."""
        return self.sounds.get(note) is not None

    def stop_all(self) -> None:
        """Stop every currently playing sound (useful on app exit)."""
        pygame.mixer.stop()

    def quit(self) -> None:
        """Shut down the pygame mixer cleanly."""
        self.stop_all()
        pygame.mixer.quit()
