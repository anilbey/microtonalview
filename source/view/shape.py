"""Shape objects."""

from view.color import RGBA, Color, VisualEffect, blend_color, frequency_to_color


class Circle:
    def __init__(
        self, time: float, frequency: float, loudness: float, confidence: float
    ):
        self.time = time
        self.frequency = frequency
        self.loudness = loudness
        self.confidence = confidence

    def compute_size(self, min_loudness: float, max_loudness: float):
        """Computes size using loudness."""
        return loudness_to_size(self.loudness, min_loudness, max_loudness)

    def compute_color(
        self, current_time: float, min_frequency: float, max_frequency: float, effect: VisualEffect = VisualEffect.DEFAULT
    ) -> RGBA:
        if abs(self.time - current_time) < 0.01:
            return Color.RED  # current circle red
        else:
            base_color = frequency_to_color(
                self.frequency, min_frequency, max_frequency, effect=effect
            )
            return blend_color(base_color, self.confidence)


def loudness_to_size(
    loudness: float, min_loudness: float, max_loudness: float
) -> float:
    """Mapping loudness to circle size."""
    normalized_loudness = (loudness - min_loudness) / (max_loudness - min_loudness)
    res = max(1.8, int(normalized_loudness * 10))
    return res * 2.5  # Scale up to make circles bigger
