"""Module responsible for drawing the porte with makam-aware microtonal pitch regions."""


import pygame
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

from view.color import RGBA, Color


def _draw_text_with_outline(
    screen, font, text, x, y, main_color: RGBA, outline_color: RGBA, outline_width
):
    # Render the outline
    outline_surf = font.render(text, True, outline_color)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:  # Offset for the outline
                screen.blit(outline_surf, (x + dx, y + dy))

    # Render the main text on top
    text_surf = font.render(text, True, main_color)
    screen.blit(text_surf, (x, y))


def hz_to_cents(ref_freq: float, target_freq: float) -> float:
    """Convert frequency difference to cents relative to ref_freq."""
    return 1200 * np.log2(target_freq / ref_freq)


def detect_pitch_regions_from_clusters(clustered_freqs_df, smoothing=2, min_prominence_ratio=0.1):
    """
    Detect pitch regions from clustered frequency centers.

    Args:
        clustered_freqs_df: Polars DataFrame with 'frequency' and 'count' columns.
    """
    avg_freqs = clustered_freqs_df["frequency"].to_numpy()
    counts = clustered_freqs_df["count"].to_numpy()

    if smoothing > 0:
        smoothed_counts = gaussian_filter1d(counts, sigma=smoothing)
    else:
        smoothed_counts = counts

    peaks, _ = find_peaks(smoothed_counts, prominence=0)

    if len(peaks) == 0:
        peaks = np.where(counts > 0)[0]

    regions = []
    for idx in peaks:
        freq = avg_freqs[idx]
        count = counts[idx]
        regions.append((freq, count))

    regions.sort(key=lambda x: x[1], reverse=True)

    return regions


def draw_frequency_regions(
    screen, top_k_freq_bins, height, min_frequency, max_frequency, padding_bottom
):
    """Draw solid light transparent gray rectangles for each frequency region with labels."""
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    font = pygame.font.SysFont(None, 20)

    regions = top_k_freq_bins
    if regions.is_empty():
        return

    # Ensure tonic_start and tonic_end are scalars
    tonic_start = regions[0]["start"]
    if hasattr(tonic_start, "item"):
        tonic_start = tonic_start.item()
    tonic_end = regions[0]["end"]
    if hasattr(tonic_end, "item"):
        tonic_end = tonic_end.item()
    tonic_center = (tonic_start + tonic_end) / 2

    width = screen.get_width()

    for row in regions.iter_rows(named=True):
        start = row["start"]
        end = row["end"]

        y1_base = (height - padding_bottom) - (end - min_frequency) * scale_y
        y2_base = (height - padding_bottom) - (start - min_frequency) * scale_y
        rect_height = y2_base - y1_base

        # --- Rectangular region: top and bottom are straight lines ---
        top_points = [(0, 0), (width, 0)]
        bottom_points = [(width, rect_height), (0, rect_height)]

        # Use a light transparent gray color for all regions
        color = Color.PORTE_REGION
        # Create a surface for the region
        region_surface = pygame.Surface((width, int(rect_height)), pygame.SRCALPHA)
        # Fill the region with a solid light gray polygon (rectangle)
        pygame.draw.polygon(region_surface, color, top_points + bottom_points)
        screen.blit(region_surface, (0, y1_base))

        freq_center = (start + end) / 2
        cents_diff = hz_to_cents(tonic_center, freq_center)
        if hasattr(cents_diff, "item"):
            cents_diff = cents_diff.item()
        cents_diff = float(cents_diff)

        if start == tonic_start and end == tonic_end:
            label = f"{freq_center:.2f} Hz"
        else:
            label = f"{cents_diff:+.0f}¢"

        # Center the text vertically within the region
        text_y = int(y1_base + rect_height / 2 - font.get_height() / 2)

        _draw_text_with_outline(
            screen,
            font,
            label,
            5,
            text_y,
            Color.NOTE_TEXT,
            Color.PORTE_OUTLINE,
            outline_width=2,
        )
