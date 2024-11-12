"""Calculation of audio specific features."""

from pathlib import Path
import librosa
import numpy as np
import polars as pl
import torchaudio
import pesto
from hmmlearn import hmm


def calculate_loudness(wav_file: Path) -> np.ndarray:
    """Calculate the loudness of each frame in the audio."""
    y, sr = librosa.load(wav_file)
    frame_length = hop_length = int(0.01 * sr)  # 0.01 seconds for frame and hop length
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)
    return rms[0]


def compute_confidence(activations):
    """
    Compute confidence as the reciprocal of the normalized entropy of the activation distribution.
    """
    # Normalize activations to sum to 1 for each frame
    probs = activations / np.sum(activations, axis=1, keepdims=True)
    # Compute entropy for each frame
    entropy = -np.sum(probs * np.log(probs + 1e-12), axis=1)
    # Normalize entropy to [0, 1]
    entropy = entropy / np.log(activations.shape[1])
    # Confidence is inverse of entropy
    confidence = 1 - entropy
    return confidence

def extract_pitch_data_frame(wav_file: Path) -> pl.DataFrame:
    """Extract pitch data using PESTO with Viterbi smoothing and return a polars DataFrame."""
    # Load the audio file using torchaudio
    x, sr = torchaudio.load(str(wav_file))
    x = x.mean(dim=0)  # Convert to mono

    # Get activations from PESTO without converting to frequency
    timesteps, _, _, activations = pesto.predict(
        x,
        sr,
        step_size=10.0,
        convert_to_freq=False,
        model_name="mir-1k",
    )

    # Convert tensors to numpy arrays
    activations = activations.detach().cpu().numpy()
    time = timesteps.detach().cpu().numpy() / 1000.0  # Convert milliseconds to seconds

    # Compute confidence based on entropy
    confidence = compute_confidence(activations)

    # Apply Viterbi smoothing
    frequency = to_viterbi_frequency(activations)

    # Create the DataFrame
    df = pl.DataFrame({"time": time, "frequency": frequency, "confidence": confidence})
    df = df.drop_nulls(subset=["frequency"])
    df = df.filter(~pl.col("frequency").is_nan())
    # Remove low-confidence data AFTER Viterbi smoothing
    df = df.filter(pl.col("confidence") > 0.7)

    df.write_csv("pesto-df.csv")
    return df

def to_local_average_frequency(salience, center=None):
    """
    Find the weighted average frequency near the center bin, using CREPE's bin-to-cents mapping.
    """
    if not hasattr(to_local_average_frequency, 'cents_mapping'):
        # Create the cents mapping as in CREPE
        n_bins = salience.shape[0]
        to_local_average_frequency.cents_mapping = (
            np.linspace(0, 7180, n_bins) + 1997.3794084376191
        )

    cents_mapping = to_local_average_frequency.cents_mapping

    if salience.ndim == 1:
        if center is None:
            center = int(np.argmax(salience))
        start = max(0, center - 4)
        end = min(len(salience), center + 5)
        salience_window = salience[start:end]
        cents_window = cents_mapping[start:end]
        product_sum = np.sum(salience_window * cents_window)
        weight_sum = np.sum(salience_window)
        avg_cents = product_sum / weight_sum
        frequency = 10 * 2 ** (avg_cents / 1200)
        return frequency
    else:
        raise ValueError("Salience must be a 1D array.")

def to_viterbi_frequency(salience):
    """
    Apply Viterbi smoothing to the salience map to obtain smoothed frequency estimates,
    matching CREPE's implementation.
    """
    n_bins = salience.shape[1]

    # Uniform prior on the starting pitch
    starting = np.ones(n_bins) / n_bins

    # Transition probabilities to induce pitch continuity (matching CREPE)
    xx, yy = np.meshgrid(np.arange(n_bins), np.arange(n_bins))
    transition = np.maximum(12 - abs(xx - yy), 0)
    transition = transition / np.sum(transition, axis=1, keepdims=True)

    # Emission probabilities
    self_emission = 0.1
    emission = (
        np.eye(n_bins) * self_emission
        + np.ones((n_bins, n_bins)) * ((1 - self_emission) / n_bins)
    )

    # Initialize the HMM model without training
    model = hmm.CategoricalHMM(n_components=n_bins, init_params="", params="")
    model.startprob_ = starting
    model.transmat_ = transition
    model.emissionprob_ = emission

    # Find the Viterbi path
    observations = np.argmax(salience, axis=1)
    path = model.predict(observations.reshape(-1, 1))

    # Compute frequency estimates using local averaging
    frequency = np.array([
        to_local_average_frequency(salience[i, :], center=path[i])
        for i in range(len(observations))
    ])

    return frequency
