"""Color representations of notes."""

import colorsys
from typing import NamedTuple


class RGB(NamedTuple):
    """Red Green Blue color representation."""
    red: float
    green: float
    blue: float

class RGBA(NamedTuple):
    """Red Green Blue Alpha color representation."""
    red: float
    green: float
    blue: float
    alpha: float


class Color:
    BLACK = RGBA(0, 0, 0, 255)
    WHITE = RGBA(255, 255, 255, 255)
    RED = RGBA(255, 0, 0, 255)
    MID_LINE_SEPARATOR = RGBA(255, 153, 51, 255)
    PORTE_OUTLINE = RGBA(252, 251, 237, 255)
    PORTE_LINE = RGBA(178, 162, 167, 255)


def frequency_to_color(frequency: float, min_freq: float, max_freq: float) -> RGB:
    """Mapping frequency to colour."""
    # Normalize frequency value
    normalized_value = (frequency - min_freq) / (max_freq - min_freq)
    # Apply a non-linear transformation to make changes more sensitive
    normalized_value = pow(normalized_value, 0.4)

    # Use HSV color space for more vibrant colors
    # Hue varies from 0 to 1, corresponding to the full range of colors
    hue = normalized_value
    saturation = 0.9  # High saturation for more vivid colors
    value = 0.9       # High value for brightness

    # Convert HSV to RGB
    rgb = colorsys.hsv_to_rgb(hue, saturation, value)
    # Scale RGB values to 0-255 range
    return RGB(rgb[0] * 255, rgb[1] * 255, rgb[2] * 255)


def blend_color(base_color: RGB, confidence: float) -> RGBA:
    """Apply alpha based on confidence to the base color."""
    alpha = int(255 * confidence)
    return RGBA(base_color.red, base_color.green, base_color.blue, alpha)
