import argparse
from contextlib import contextmanager
import pygame
import polars as pl

from audio_features import calculate_loudness
from view.porte import draw_frequency_lines
from dataframe_operations import (
    add_loudness,
    compute_x_positions_lazy,
    compute_y_positions_lazy,
    filter_data_by_time_window_lazy,
    get_top_k_frequency_bins,
)
from view.shape import Circle
from view.color import Color
from event import handle_quit_event, is_music_playing
from view.text_display import fps_textbox


@contextmanager
def loading_screen(screen: pygame.Surface, width: int, height: int, image_path: str):
    """Display the loading image."""
    loading_image = pygame.image.load(image_path)
    screen.blit(
        loading_image,
        (
            width // 2 - loading_image.get_width() // 2,
            height // 2 - loading_image.get_height() // 2,
        ),
    )
    pygame.display.flip()  # Update the display to show the loading image

    try:
        yield  # Control is returned to the main program for the duration of the context
    finally:
        # Clear the screen after loading is complete
        screen.fill(Color.WHITE)
        pygame.display.flip()


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")

    # Add the arguments
    parser.add_argument("features", help="The features csv for rendering")
    parser.add_argument("audio", help="Path to the .wav file")

    # Execute the parse_args() method
    args = parser.parse_args()
    # Load the audio file
    audio_file = args.audio
    icon = pygame.image.load("logo.png")
    pygame.display.set_icon(icon)

    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    width, height = 1920, 1080
    screen = pygame.display.set_mode((width, height), pygame.SRCALPHA)
    screen.fill(Color.WHITE)
    pygame.display.set_caption("Microtonal View")

    with loading_screen(screen, width, height, "microtonal-view.png"):
        # Use Polars to load data from the features CSV file
        pitch_data = pl.read_csv(args.features)

        # Calculate loudness and update pitch data
        loudness = calculate_loudness(audio_file)
        pitch_data = add_loudness(pitch_data, loudness)

        # Remove rows with confidence less than 0.5
        pitch_data = pitch_data.filter(pitch_data["confidence"] > 0.5)
        pygame.mixer.music.load(audio_file)

    min_frequency = pitch_data["frequency"].min()
    max_frequency = pitch_data["frequency"].max()

    min_loudness = pitch_data["loudness"].min()
    max_loudness = pitch_data["loudness"].max()

    # Define padding as a percentage of the height
    padding_percent = 0.15  # 15% padding at the bottom
    padding_bottom = int(height * padding_percent)

    # Adjust scale_y to fit within the screen, considering padding
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    scale_x = width / 5

    # Create a surface for static elements
    static_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.line(
        static_elements_surface,
        Color.MID_LINE_SEPARATOR,
        (width // 2, 0),
        (width // 2, height),
        1,
    )
    top_k_freq_bins = get_top_k_frequency_bins(pitch_data, bin_size=30, k=10)
    draw_frequency_lines(
        static_elements_surface,
        top_k_freq_bins,
        height,
        min_frequency,
        max_frequency,
        padding_bottom,
    )

    # Create a separate surface for dynamic elements (circles)
    dynamic_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

    running = True
    clock = pygame.time.Clock()

    circle = Circle(0, 0, 0, 0)  # the drawing circle object
    lazy_pitch_data = pitch_data.lazy()
    pygame.mixer.music.play()
    while running:
        running = handle_quit_event() and is_music_playing()

        current_time = (
            pygame.mixer.music.get_pos() / 1000.0
        )  # offset to start slightly earlier
        # Get the window frame lazily
        dataframe_window_to_display_lazy = filter_data_by_time_window_lazy(
            lazy_pitch_data, current_time
        ).with_columns(
            [
                compute_x_positions_lazy(current_time, scale_x).alias("x"),
                compute_y_positions_lazy(
                    height, padding_bottom, min_frequency, scale_y
                ).alias("y"),
            ]
        )
        dataframe_window_to_display = dataframe_window_to_display_lazy.collect()

        # Clear the dynamic elements surface each frame
        dynamic_elements_surface.fill(Color.WHITE)

        for row in dataframe_window_to_display.iter_rows(named=True):
            circle.time = row["time"]
            circle.frequency = row["frequency"]
            circle.loudness = row["loudness"]
            circle.confidence = row["confidence"]

            circle_size = circle.compute_size(min_loudness, max_loudness)
            color = circle.compute_color(current_time, min_frequency, max_frequency)

            circle_surface = pygame.Surface(
                (2 * circle_size, 2 * circle_size), pygame.SRCALPHA
            )
            pygame.draw.circle(
                circle_surface, color, (circle_size, circle_size), circle_size
            )
            dynamic_elements_surface.blit(
                circle_surface,
                (int(row["x"]) - circle_size, int(row["y"]) - circle_size),
            )

        # Draw the updated dynamic elements over the static ones
        screen.blit(dynamic_elements_surface, (0, 0))
        # Draw the static elements to the screen
        screen.blit(static_elements_surface, (0, 0))

        screen.blit(fps_textbox(clock, font_size=36, color=Color.BLACK), dest=(10, 10))

        pygame.display.flip()
        clock.tick(60)  # desired FPS

    pygame.quit()


main()