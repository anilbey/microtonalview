"""Calculation of audio specific features."""

from pathlib import Path
import crepe
import librosa
import numpy as np
import polars as pl


def calculate_loudness(wav_file: Path) -> np.ndarray:
    """Calculate the loudness of each frame in the audio."""
    y, sr = librosa.load(wav_file)
    frame_length = hop_length = int(0.01 * sr)  # 0.01 seconds for frame and hop length
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)
    return rms[0]


def extract_pitch_data_frame(wav_file: Path) -> pl.DataFrame:
    """Extract pitch data using CREPE and return a polars DataFrame."""
    y, sr = librosa.load(wav_file, sr=16000)  # CREPE requires 16kHz audio
    time, frequency, confidence, activation = crepe.predict(
        y, sr, viterbi=True, step_size=10
    )
    df = pl.DataFrame({"time": time, "frequency": frequency, "confidence": confidence})

    return df
