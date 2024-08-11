import argparse
import pygame
import polars as pl

from porte import draw_frequency_lines
from dataframe_operations import get_top_k_frequency_bins
from shape import Circle
from color import Color
from event import handle_quit_event


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
    screen.fill(Color.WHITE)
    pygame.display.set_caption("Microtonal Pitch Visualisation")

    # Use Polars to load data from the features CSV file
    data = pl.read_csv(args.features)
    # remove rows with confidence less than 0.5
    data = data.filter(data["confidence"] > 0.5)

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
        static_elements_surface, Color.MID_LINE_SEPARATOR, (width // 2, 0), (width // 2, height), 1
    )
    top_k_freq_bins = get_top_k_frequency_bins(data, bin_size=30, k=10)
    draw_frequency_lines(static_elements_surface, top_k_freq_bins, height, min_frequency, max_frequency, padding_bottom)

    # Create a separate surface for dynamic elements (circles)
    dynamic_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)


    font = pygame.font.SysFont(None, 36)
    pygame.mixer.music.play()

    running = True
    clock = pygame.time.Clock()

    while running:
        running = handle_quit_event()

        current_time = pygame.mixer.music.get_pos() / 1000.0
        # Use Polars for data filtering
        relevant_data = data.filter(
            (data["time"] >= current_time - 2.5) & (data["time"] <= current_time + 2.5)
        )

        # Clear the dynamic elements surface each frame
        dynamic_elements_surface.fill(Color.WHITE)

        for row in relevant_data.iter_rows(named=True):
            circle = Circle(
                time=row["time"],
                frequency=row["frequency"],
                loudness=row["loudness"],
                confidence=row["confidence"]
            )

            x = circle.compute_x_coordinate(current_time, scale_x)
            y = circle.compute_y_coordinate(scale_y, min_frequency, height, padding_bottom)
            circle_size = circle.compute_size(min_loudness, max_loudness)
            color = circle.compute_color(current_time, min_frequency, max_frequency)

            circle_surface = pygame.Surface((2 * circle_size, 2 * circle_size), pygame.SRCALPHA)
            pygame.draw.circle(
                circle_surface,
                color,
                (circle_size, circle_size),
                circle_size
            )
            dynamic_elements_surface.blit(circle_surface, (int(x) - circle_size, int(y) - circle_size))

        # Draw the updated dynamic elements over the static ones
        screen.blit(dynamic_elements_surface, (0, 0))
        # Draw the static elements to the screen
        screen.blit(static_elements_surface, (0, 0))

        fps = clock.get_fps()
        fps_text = font.render(f"{fps:.2f} FPS", True, Color.BLACK)
        screen.blit(fps_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)  # desired FPS

        # Check if music is still playing
        if not pygame.mixer.music.get_busy():
            running = False

    pygame.quit()


main()
