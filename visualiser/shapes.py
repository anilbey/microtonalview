"""Shape objects."""
from color import RGBA, blend_color, frequency_to_color

class Circle:
    def __init__(self, time: float, frequency: float, loudness: float, confidence: float):
        self.time = time
        self.frequency = frequency
        self.loudness = loudness
        self.confidence = confidence

    def compute_x_coordinate(self, current_time: float, scale_x: float) -> float:
        return (self.time - current_time + 2.5) * scale_x

    def compute_y_coordinate(self, scale_y: float, min_frequency: float, height: int, padding_bottom: int) -> float:
        return (height - padding_bottom) - (self.frequency - min_frequency) * scale_y

    def compute_size(self, min_loudness: float, max_loudness: float):
        """Computes size using loudness."""
        return loudness_to_size(self.loudness, min_loudness, max_loudness)

    def compute_color(self, current_time: float, min_frequency: float, max_frequency: float) -> RGBA:
        if abs(self.time - current_time) < 0.01:
            return RGBA(255, 0, 0, 255)  # current circle red
        else:
            base_color = frequency_to_color(self.frequency, min_frequency, max_frequency)
            return blend_color(base_color, self.confidence)

    def should_draw(self) -> bool:
        return self.confidence >= 0.5

def loudness_to_size(loudness: float, min_loudness: float, max_loudness: float) -> float:
    """Mapping loudness to circle size."""
    normalized_loudness = (loudness - min_loudness) / (max_loudness - min_loudness)
    res = max(1, int(normalized_loudness * 10))  # Scale and ensure minimum size of 1
    return res * 2.5  # Scale up to make circles bigger
