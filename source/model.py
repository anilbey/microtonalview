from dataclasses import dataclass
import polars as pl


@dataclass
class Pitch:
    annotated_pitch_data_frame: pl.DataFrame
    top_k_freq_bins: pl.DataFrame
    min_frequency: float
    max_frequency: float
    min_loudness: float
    max_loudness: float
