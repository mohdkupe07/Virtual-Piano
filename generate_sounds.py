"""
generate_sounds.py
------------------
Utility script to synthesise piano-like .wav files for C, D, E, F, G.

Run this ONCE before running main.py if you do not have real piano samples:

    python generate_sounds.py

It writes C.wav, D.wav, E.wav, F.wav, G.wav into the sounds/ directory.

The waveform is a sum of harmonics (fundamental + overtones) with an
exponential decay envelope to approximate the natural sound of a piano key.
No external libraries are required beyond NumPy.
"""

import os
import struct
import math
import numpy as np


# ── Note frequencies (Hz) – C4 to G4 ──────────────────────────────────────
NOTE_FREQUENCIES = {
    "C": 261.63,   # C4 (middle C)
    "D": 293.66,   # D4
    "E": 329.63,   # E4
    "F": 349.23,   # F4
    "G": 392.00,   # G4
}

SAMPLE_RATE   = 44100   # Hz
DURATION      = 1.5     # seconds per note
AMPLITUDE     = 0.6     # 0.0–1.0, leave headroom
DECAY         = 4.0     # exponential decay rate (higher = shorter sustain)
SOUNDS_DIR    = "sounds"


def synthesise_note(freq: float) -> np.ndarray:
    """
    Generate a piano-like mono waveform for the given fundamental frequency.

    The timbre is shaped by summing the fundamental with several harmonics,
    each at decreasing amplitude.  An exponential envelope is applied so the
    note fades naturally rather than cutting off abruptly.

    Args:
        freq: Fundamental frequency in Hz.

    Returns:
        NumPy array of float32 samples in [-1, 1].
    """
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)

    # Harmonic series: [fundamental, 2nd, 3rd, 4th, 5th]
    # Amplitudes follow a roughly 1/n roll-off typical of piano strings.
    harmonics = [
        (1.0,  1.00),   # fundamental
        (2.0,  0.50),   # octave
        (3.0,  0.25),   # fifth above octave
        (4.0,  0.12),   # two octaves
        (5.0,  0.06),   # third above two octaves
    ]

    wave = np.zeros_like(t, dtype=np.float32)
    for harmonic, amp in harmonics:
        wave += amp * np.sin(2 * np.pi * freq * harmonic * t).astype(np.float32)

    # Normalise to [-1, 1] then scale by master amplitude
    max_val = np.max(np.abs(wave))
    if max_val > 0:
        wave = wave / max_val * AMPLITUDE

    # Apply exponential decay envelope
    envelope = np.exp(-DECAY * t).astype(np.float32)
    wave *= envelope

    return wave


def write_wav(filepath: str, samples: np.ndarray, sample_rate: int = 44100) -> None:
    """
    Write a mono float32 NumPy array as a 16-bit PCM WAV file.

    Args:
        filepath:    Output path (e.g. 'sounds/C.wav').
        samples:     Float32 array in [-1, 1].
        sample_rate: Sample rate in Hz.
    """
    # Convert float32 → int16
    pcm = (samples * 32767).astype(np.int16)
    num_samples    = len(pcm)
    num_channels   = 1       # mono
    bits_per_sample = 16
    byte_rate      = sample_rate * num_channels * bits_per_sample // 8
    block_align    = num_channels * bits_per_sample // 8
    data_size      = num_samples * block_align
    chunk_size     = 36 + data_size

    with open(filepath, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", chunk_size))
        f.write(b"WAVE")
        # fmt sub-chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))            # sub-chunk size
        f.write(struct.pack("<H", 1))             # PCM format
        f.write(struct.pack("<H", num_channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))
        # data sub-chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(pcm.tobytes())


def main() -> None:
    os.makedirs(SOUNDS_DIR, exist_ok=True)

    for note, freq in NOTE_FREQUENCIES.items():
        samples  = synthesise_note(freq)
        filepath = os.path.join(SOUNDS_DIR, f"{note}.wav")
        write_wav(filepath, samples)
        print(f"Generated: {filepath}  ({freq:.2f} Hz)")

    print("\nAll sound files created in the 'sounds/' folder.")
    print("You can now run: python main.py")


if __name__ == "__main__":
    main()
