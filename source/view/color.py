"""Color representations of notes."""

import colorsys
import math
from enum import StrEnum
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


class VisualEffect(StrEnum):
    """Visual effect options for frequency color mapping."""
    
    DEFAULT = "default"
    GRADIENT = "gradient"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    RAINBOW = "rainbow"
    SPECTRUM = "spectrum"


class Color:
    BLACK = RGBA(0, 0, 0, 255)
    WHITE = RGBA(255, 255, 255, 255)
    RED = RGBA(255, 0, 0, 255)
    MID_LINE_SEPARATOR = RGBA(255, 153, 51, 255)
    PORTE_OUTLINE = RGBA(252, 251, 237, 255)
    PORTE_LINE = RGBA(178, 162, 167, 255)
    NOTE_TEXT = RGBA(33, 40, 45, 255)


def frequency_to_color(frequency: float, min_freq: float, max_freq: float, effect: VisualEffect = VisualEffect.DEFAULT) -> RGB:
    """Mapping frequency to colour with shader-like effects.
    
    Args:
        frequency: The frequency to convert to color
        min_freq: Minimum frequency in the range
        max_freq: Maximum frequency in the range
        effect: Visual effect to apply from VisualEffect enum
    
    Returns:
        RGB color representing the frequency
    """
    # Normalize frequency value
    normalized_value = (frequency - min_freq) / (max_freq - min_freq)
    
    if effect == VisualEffect.GRADIENT:
        # Smooth gradient with enhanced saturation at extremes
        hue = normalized_value
        saturation = 0.7 + 0.3 * math.sin(normalized_value * math.pi)
        value = 0.85 + 0.15 * math.cos(normalized_value * math.pi * 2)
    
    elif effect == VisualEffect.VIBRANT:
        # More vibrant colors with non-linear mapping
        normalized_value = pow(normalized_value, 0.4)
        hue = normalized_value
        saturation = 0.9
        value = 1.0
    
    elif effect == VisualEffect.PASTEL:
        # Pastel colors with higher brightness and lower saturation
        hue = normalized_value
        saturation = 0.5 + 0.2 * math.sin(normalized_value * math.pi * 3)
        value = 0.9 + 0.1 * math.sin(normalized_value * math.pi * 5)
    
    elif effect == VisualEffect.RAINBOW:
        # Rainbow effect with multiple hue cycles
        hue = (normalized_value * 3) % 1.0
        saturation = 0.8
        value = 0.9
    
    elif effect == VisualEffect.SPECTRUM:
        # Physics-inspired spectrum with non-linear mapping
        # Map to visible light spectrum (approximately 380-750nm)
        normalized_value = pow(normalized_value, 0.5)  # Non-linear mapping
        hue = normalized_value * 0.8  # Keep within 0-0.8 range for more natural colors
        saturation = 0.85 + 0.15 * math.sin(normalized_value * math.pi * 4)
        value = 0.9 + 0.1 * math.sin(normalized_value * math.pi * 8)
    
    else:  # default
        # Original effect with slight enhancement
        normalized_value = pow(normalized_value, 0.4)
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
