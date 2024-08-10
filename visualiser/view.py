import argparse
import colorsys
import pygame
import polars as pl

from porte import draw_frequency_lines
from dataframe_operations import get_top_k_frequency_bins

def frequency_to_color(frequency: float, min_freq: float, max_freq: float) -> tuple[float, float, float]:
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
    return rgb[0] * 255, rgb[1] * 255, rgb[2] * 255


def blend_color(base_color: tuple[float, float, float], confidence: float) -> tuple[float, float, float, float]:
    """Apply alpha based on confidence to the base color."""
    alpha = int(255 * confidence)
    return base_color + (alpha,)


def loudness_to_size(loudness: float, min_loudness: float, max_loudness: float) -> float:
    """Mapping loudness to circle size."""
    normalized_loudness = (loudness - min_loudness) / (max_loudness - min_loudness)
    res = max(1, int(normalized_loudness * 10))  # Scale and ensure minimum size of 1
    return res * 2.5  # Scale up to make circles bigger


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")

    # Add the arguments
    parser.add_argument("features", help="The features csv for rendering")
    parser.add_argument("audio", help="Path to the .wav file")

    # Execute the parse_args() method
    args = parser.parse_args()

    icon = pygame.image.load('logo.png')
    pygame.display.set_icon(icon)

    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    width, height = 1920, 1080
    screen = pygame.display.set_mode((width, height), pygame.SRCALPHA)
    screen.fill((255, 255, 255))  # white
    pygame.display.set_caption("Microtonal Pitch Visualisation")

    # Use Polars to load data from the features CSV file
    data = pl.read_csv(args.features)

    top_k_freq_bins = get_top_k_frequency_bins(data, bin_size=30, k=10)
    # Load the audio file
    audio_file = args.audio
    pygame.mixer.music.load(audio_file)

    min_frequency = data["frequency"].min()
    max_frequency = data["frequency"].max()

    min_loudness = data["loudness"].min()
    max_loudness = data["loudness"].max()

    # Define padding as a percentage of the height
    padding_percent = 0.15  # 15% padding at the bottom
    padding_bottom = int(height * padding_percent)

    # Adjust scale_y to fit within the screen, considering padding
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    scale_x = width / 5

    # Create a surface for static elements
    static_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.line(
        static_elements_surface, (255, 153, 51), (width // 2, 0), (width // 2, height), 1
    )
    draw_frequency_lines(static_elements_surface, top_k_freq_bins, height, min_frequency, max_frequency, padding_bottom)

    # Create a separate surface for dynamic elements (circles)
    dynamic_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)


    font = pygame.font.SysFont(None, 36)
    pygame.mixer.music.play()

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        current_time = pygame.mixer.music.get_pos() / 1000.0
        # Use Polars for data filtering
        relevant_data = data.filter(
            (data["time"] >= current_time - 2.5) & (data["time"] <= current_time + 2.5)
        )

        # Clear the dynamic elements surface each frame
        dynamic_elements_surface.fill((255, 255, 255))

        for row in relevant_data.iter_rows(named=True):
            x = (row["time"] - current_time + 2.5) * scale_x
            y = (height - padding_bottom) - (row["frequency"] - min_frequency) * scale_y
            circle_size = loudness_to_size(row["loudness"], min_loudness, max_loudness)

            # if confidence < 0.5, don't draw
            if row["confidence"] < 0.5:
                continue

            is_current_circle = (
                abs(row["time"] - current_time) < 0.01
            )  # Adjust the threshold as needed

            if is_current_circle:
                color = (255, 0, 0)  # current circle red
            else:
                base_color = frequency_to_color(
                    row["frequency"], min_frequency, max_frequency
                )
                color = blend_color(base_color, row["confidence"])

            circle_surface = pygame.Surface(
                (2 * circle_size, 2 * circle_size), pygame.SRCALPHA
            )
            pygame.draw.circle(
                circle_surface, color, (circle_size, circle_size), circle_size
            )
            dynamic_elements_surface.blit(circle_surface, (int(x) - circle_size, int(y) - circle_size))

        # Draw the updated dynamic elements over the static ones
        screen.blit(dynamic_elements_surface, (0, 0))
        # Draw the static elements to the screen
        screen.blit(static_elements_surface, (0, 0))

        fps = clock.get_fps()
        fps_text = font.render(f"{fps:.2f} FPS", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)  # desired FPS

        # Check if music is still playing
        if not pygame.mixer.music.get_busy():
            running = False

    pygame.quit()


main()
