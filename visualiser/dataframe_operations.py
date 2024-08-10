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
