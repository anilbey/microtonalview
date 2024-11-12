"""Calculation of audio specific features."""

from pathlib import Path
import torchcrepe
import torch
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
    """Extract pitch data using torchcrepe and return a polars DataFrame."""
    audio, sr = torchcrepe.load.audio(str(wav_file))

    # Convert to mono if necessary
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)

    # Set device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    audio = audio.to(device)

    # Compute hop length for 10 ms steps
    hop_length = int(sr * 0.01)

    # Set frequency range (50 Hz to 1200 Hz)
    fmin, fmax = 50.0, 1200.0
    model = 'full'
    batch_size = 1024

    pitch, periodicity = torchcrepe.predict(
        audio,
        sr,
        hop_length,
        fmin,
        fmax,
        model,
        batch_size=batch_size,
        device=device,
        return_periodicity=True
    )
    num_frames = pitch.shape[-1]
    time = np.arange(num_frames) * hop_length / sr

    frequency = pitch.squeeze().cpu().numpy()
    confidence = periodicity.squeeze().cpu().numpy()

    df = pl.DataFrame({
        "time": time,
        "frequency": frequency,
        "confidence": confidence
    })

    return df
