import argparse
from concurrent.futures import ThreadPoolExecutor
import sys
import polars as pl
import pygame


from audio_features import calculate_loudness, extract_pitch_data_frame
from caching import hash_file, load_from_cache, save_to_cache
from view.screen import loading_screen
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


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")

    # Add the arguments
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

    # Get the display size for fullscreen mode
    display_info = pygame.display.Info()
    width, height = display_info.current_w, display_info.current_h
    screen = pygame.display.set_mode(
        (width, height), pygame.FULLSCREEN | pygame.SRCALPHA
    )
    screen.fill((255, 255, 255))  # White background
    pygame.display.set_caption("Microtonal View")

    with ThreadPoolExecutor() as executor:
        with loading_screen(screen, width, height, "microtonal-view.png") as loader:
            audio_hash: str = hash_file(audio_file)
            cached_data: pl.DataFrame = load_from_cache(audio_hash)
            if cached_data is not None:
                pitch_data = cached_data
                print("Using cached data...")
            else:
                # Start the loading task in the background
                future = executor.submit(extract_pitch_data_frame, audio_file)
                print("Loading pitch data...")

                while not future.done():
                    # Handle events
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()

                    loader.display_loading_screen()  # Redraw the loading screen
                    loader.update_stdout_display()

                    # Control the UI refresh rate
                    pygame.time.Clock().tick(20)

                # Get the result of the task
                pitch_data = future.result()
                save_to_cache(audio_hash, pitch_data)

            # Continue after loading is complete
            print("Calculating loudness...")
            loader.display_loading_screen()
            loader.update_stdout_display()
            loudness = calculate_loudness(audio_file)

            pitch_data = add_loudness(pitch_data, loudness)

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
        )
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

        screen.blit(dynamic_elements_surface, (0, 0))
        screen.blit(static_elements_surface, (0, 0))

        screen.blit(fps_textbox(clock, font_size=36, color=Color.BLACK), dest=(10, 10))

        pygame.display.flip()
        clock.tick(60)  # desired FPS

    pygame.quit()


main()
