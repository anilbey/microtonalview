"""Operations that are performed on DataFrames."""

import numpy as np
import polars as pl

from audio_features import calculate_loudness
from model import Pitch

from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


def find_actual_frequencies_from_peaks(
    data: pl.DataFrame,
    smoothing_sigma: float = 2.0,
    peak_prominence: float = 0.05,
    peak_distance_hz: float = 5.0,
    freq_tolerance: float = 3.0
) -> pl.DataFrame:
    """
    Detect important frequency regions by finding peaks in a smoothed frequency histogram,
    and returning frequency *ranges* (start, end) for each region.

    Returns:
        Polars DataFrame with columns ['start', 'end', 'count'].
    """

    freqs = data["frequency"].to_numpy()

    min_freq, max_freq = freqs.min(), freqs.max()
    bin_width = 1.0
    bins = np.arange(min_freq, max_freq + bin_width, bin_width)

    hist_counts, bin_edges = np.histogram(freqs, bins=bins)
    smoothed_counts = gaussian_filter1d(hist_counts, sigma=smoothing_sigma)

    peaks, _ = find_peaks(
        smoothed_counts,
        prominence=peak_prominence * np.max(smoothed_counts),
        distance=int(peak_distance_hz / bin_width),
    )

    peak_freqs = bin_edges[peaks]

    start_freqs = []
    end_freqs = []
    counts = []

    for pf in peak_freqs:
        diffs = np.abs(freqs - pf)
        close_indices = np.where(diffs <= freq_tolerance)[0]
        if len(close_indices) == 0:
            continue
        close_freqs = freqs[close_indices]

        start = close_freqs.min()
        end = close_freqs.max()
        count = len(close_freqs)

        start_freqs.append(start)
        end_freqs.append(end)
        counts.append(count)

    return pl.DataFrame({
        "start": start_freqs,
        "end": end_freqs,
        "count": counts
    }).sort("count", descending=True)



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
    processed_pitch_data = process_pitch_data_frame(pitch_data, audio_file)

    min_frequency = processed_pitch_data["frequency"].min()
    max_frequency = processed_pitch_data["frequency"].max()

    min_loudness = processed_pitch_data["loudness"].min()
    max_loudness = processed_pitch_data["loudness"].max()

    # Extract pitch regions using peak-based method
    clustered_freqs = find_actual_frequencies_from_peaks(
        processed_pitch_data,
        smoothing_sigma=2.0,
        peak_prominence=0.05,
        peak_distance_hz=5.0,
        freq_tolerance=3.0
    )

    return Pitch(
        annotated_pitch_data_frame=processed_pitch_data,
        top_k_freq_bins=clustered_freqs,
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
