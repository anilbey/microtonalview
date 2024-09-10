"""Operations that are performed on DataFrames."""

import numpy as np
import polars as pl

from audio_features import calculate_loudness
from model import Pitch


def _calculate_frequency_bins(
    df: pl.DataFrame, bin_size: int
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate the frequency bin usage."""
    min_freq = df["frequency"].min()
    max_freq = df["frequency"].max()
    bins: np.ndarray = np.arange(min_freq, max_freq, bin_size)
    freq_counts, _ = np.histogram(df["frequency"], bins)
    return freq_counts, bins


def get_top_k_frequency_bins(data: pl.DataFrame, bin_size: int, k: int) -> pl.DataFrame:
    # Calculate frequency bins
    freq_counts, bins = _calculate_frequency_bins(data, bin_size)

    # Create a DataFrame for frequency bin data
    bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
    freq_df = pl.DataFrame({"Frequency Range": bin_labels, "Count": freq_counts})

    # Get top k frequency bins
    top_k_freq_bins = freq_df.top_k(k, by="Count")
    return top_k_freq_bins


def add_loudness(data: pl.DataFrame, loudness: np.ndarray) -> pl.DataFrame:
    """Add loudness data to the DataFrame."""
    # Ensure loudness array is not longer than the DataFrame
    loudness = loudness[: len(data)]
    return data.with_columns(pl.Series("loudness", loudness))


def filter_data_by_time_window_lazy(
    data: pl.LazyFrame, current_time: float, window_size: float = 2.5
) -> pl.LazyFrame:
    """
    Filter the data to include only rows where the 'time' is within the specified window around the current time.

    Args:
        data (pl.LazyFrame): The input LazyFrame containing a 'time' column.
        current_time (float): The current time to filter around.
        window_size (float): The window size around the current time (default is 2.5 seconds).

    Returns:
        pl.LazyFrame: The filtered LazyFrame containing rows within the specified time window.
    """
    return data.filter(
        (pl.col("time") >= current_time - window_size)
        & (pl.col("time") <= current_time + window_size)
    )


def compute_x_positions_lazy(current_time: float, scale_x: float) -> pl.Expr:
    return (pl.col("time") - current_time + 2.5) * scale_x


def compute_y_positions_lazy(
    height: int, padding_bottom: int, min_frequency: float, scale_y: float
) -> pl.Expr:
    return (height - padding_bottom) - (pl.col("frequency") - min_frequency) * scale_y


def process_pitch_data(pitch_data: pl.DataFrame, audio_file: str) -> Pitch:
    """Process the pitch data and return a Pitch object."""
    processed_pitch_data = process_pitch_data_frame(pitch_data, audio_file)

    min_frequency = processed_pitch_data["frequency"].min()
    max_frequency = processed_pitch_data["frequency"].max()

    min_loudness = processed_pitch_data["loudness"].min()
    max_loudness = processed_pitch_data["loudness"].max()

    top_k_freq_bins = get_top_k_frequency_bins(processed_pitch_data, bin_size=30, k=10)

    return Pitch(
        annotated_pitch_data_frame=processed_pitch_data,
        top_k_freq_bins=top_k_freq_bins,
        min_frequency=min_frequency,
        max_frequency=max_frequency,
        min_loudness=min_loudness,
        max_loudness=max_loudness,
    )


def process_pitch_data_frame(pitch_data: pl.DataFrame, audio_file: str) -> pl.DataFrame:
    """Add loudness, filter out rows with low confidence."""
    loudness = calculate_loudness(audio_file)
    pitch_data = add_loudness(pitch_data, loudness)

    # Filter out low-confidence pitch data
    pitch_data = pitch_data.filter(pitch_data["confidence"] > 0.5)
    return pitch_data
