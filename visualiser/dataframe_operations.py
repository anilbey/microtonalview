"""Operations that are performed on DataFrames."""

import numpy as np
import polars as pl


def _calculate_frequency_bins(df: pl.DataFrame, bin_size: int) -> tuple[np.ndarray, np.ndarray]:
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
    bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]
    freq_df = pl.DataFrame({
        "Frequency Range": bin_labels,
        "Count": freq_counts
    })

    # Get top k frequency bins
    top_k_freq_bins = freq_df.top_k(k, by="Count")
    return top_k_freq_bins


def filter_data_by_time_window(data: pl.DataFrame, current_time: float, window_size: float = 2.5) -> pl.DataFrame:
    """
    Filter the data to include only rows where the 'time' is within the specified window around the current time.

    Args:
        data (pl.DataFrame): The input DataFrame containing a 'time' column.
        current_time (float): The current time to filter around.
        window_size (float): The window size around the current time (default is 2.5 seconds).

    Returns:
        pl.DataFrame: The filtered DataFrame containing rows within the specified time window.
    """
    return data.filter(
        (pl.col("time") >= current_time - window_size) & (pl.col("time") <= current_time + window_size)
    )


def compute_x_positions(relevant_data: pl.DataFrame, current_time: float, scale_x: float) -> pl.Series:
    return (relevant_data["time"] - current_time + 2.5) * scale_x

def compute_y_positions(relevant_data: pl.DataFrame, height: int, padding_bottom: int, min_frequency: float, scale_y: float) -> pl.Series:
    return (height - padding_bottom) - (relevant_data["frequency"] - min_frequency) * scale_y
