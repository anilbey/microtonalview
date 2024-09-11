import argparse
from concurrent.futures import ThreadPoolExecutor
import polars as pl
import pygame
import pygame_gui
from pydub import AudioSegment
from audio_features import extract_pitch_data_frame
from caching import hash_file, load_from_cache, save_to_cache
from controller.audio_player import AudioPlayer
from controller.event_handler import handle_loading_screen_events, handle_visualiser_events
from controller.program_state import ProgramState
from view.loading_screen import loading_screen
from view.porte import draw_frequency_lines
from dataframe_operations import (
    compute_x_positions_lazy,
    compute_y_positions_lazy,
    filter_data_by_time_window_lazy,
    process_pitch_data,
)
from view.shape import Circle
from view.color import Color
from view.text_display import fps_textbox


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")
    parser.add_argument("audio", help="Path to the .wav file")
    args = parser.parse_args()
    audio_file = args.audio

    icon = pygame.image.load("logo.png")
    pygame.display.set_icon(icon)

    pygame.init()
    pygame.font.init()

    # Get the display size for fullscreen mode
    display_info = pygame.display.Info()
    width, height = display_info.current_w, display_info.current_h
    top_area_height = 60  # Height reserved for buttons and FPS display
    usable_height = height - top_area_height  # Height available for the rest of the program

    screen = pygame.display.set_mode(
        (width, height), pygame.FULLSCREEN | pygame.SRCALPHA
    )
    pygame.display.set_caption("Microtonal View")

    # Initialize pygame_gui
    manager = pygame_gui.UIManager((width, height))
    close_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width - 45, 10), (35, 35)),
        text="X",
        manager=manager,
        object_id="#close_button",
    )

    minimize_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width - 85, 10), (35, 35)),
        text="-",
        manager=manager,
        object_id="#minimize_button",
    )

    with loading_screen(screen, width, height, "microtonal-view.png") as loader:
        audio_hash: str = hash_file(audio_file)
        cached_data: pl.DataFrame | None = load_from_cache(audio_hash)
        with ThreadPoolExecutor(max_workers=2) as executor:
            if cached_data is not None:
                raw_pitch_data = cached_data
                print("Using cached data...")
            else:
                future = executor.submit(extract_pitch_data_frame, audio_file)
                print("Extracting pitch data...")

                while not future.done():  # Frame loop: extract pitch data
                    handle_loading_screen_events(manager, close_button, minimize_button)

                    loader.display_loading_screen()
                    loader.update_stdout_display()
                    manager.update(0.01)
                    manager.draw_ui(screen)
                    pygame.display.flip()
                    pygame.time.Clock().tick(20)

                raw_pitch_data = future.result()
                save_to_cache(audio_hash, raw_pitch_data)

            print("Processing pitch data...")
            future_process = executor.submit(process_pitch_data, raw_pitch_data, audio_file)

            while not future_process.done():  # Frame loop: process pitch data
                handle_loading_screen_events(manager, close_button, minimize_button)
                loader.display_loading_screen()
                loader.update_stdout_display()
                manager.update(0.01)
                manager.draw_ui(screen)
                pygame.display.flip()
                pygame.time.Clock().tick(20)
            pitch = future_process.result()

    padding_percent = 0.15
    padding_bottom = int(usable_height * padding_percent)

    scale_y = (usable_height - padding_bottom) / (pitch.max_frequency - pitch.min_frequency)
    scale_x = width / 5

    static_elements_surface = pygame.Surface((width, usable_height), pygame.SRCALPHA)
    pygame.draw.line(
        static_elements_surface,
        Color.MID_LINE_SEPARATOR,
        (width // 2, 0),
        (width // 2, usable_height),
        1,
    )

    draw_frequency_lines(
        static_elements_surface,
        pitch.top_k_freq_bins,
        usable_height,
        pitch.min_frequency,
        pitch.max_frequency,
        padding_bottom,
    )

    dynamic_elements_surface = pygame.Surface((width, usable_height), pygame.SRCALPHA)

    program_state = ProgramState.RUNNING
    clock = pygame.time.Clock()

    circle = Circle(0, 0, 0, 0)
    lazy_pitch_data = pitch.annotated_pitch_data_frame.lazy()

    audio_segment = AudioSegment.from_wav(audio_file)
    player = AudioPlayer(audio_segment)

    slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((20, height - 60), (width - 40, 40)),
        start_value=0,
        value_range=(0, 64),
        manager=manager,
        object_id="#slider",
    )

    music_length = len(audio_segment) / 1000.0  # in seconds

    player.play()  # Start playback

    while player.is_playing() and program_state == ProgramState.RUNNING:
        time_delta = clock.tick(60) / 1000.0

        program_state = handle_visualiser_events(
            manager, close_button, minimize_button, player, slider, music_length
        )
        current_time = player.get_elapsed_time()
        slider_percentage = (current_time / music_length) * slider.value_range[1]
        slider.set_current_value(slider_percentage)

        dataframe_window_to_display_lazy = filter_data_by_time_window_lazy(
            lazy_pitch_data, current_time
        ).with_columns(
            [
                compute_x_positions_lazy(current_time, scale_x).alias("x"),
                compute_y_positions_lazy(
                    usable_height, padding_bottom, pitch.min_frequency, scale_y
                ).alias("y"),
            ]
        )
        dataframe_window_to_display = dataframe_window_to_display_lazy.collect()

        # Clear the screen with white color (including the top area)
        screen.fill(Color.WHITE)

        dynamic_elements_surface.fill(Color.WHITE)
        for row in dataframe_window_to_display.iter_rows(named=True):
            circle.time = row["time"]
            circle.frequency = row["frequency"]
            circle.loudness = row["loudness"]
            circle.confidence = row["confidence"]

            circle_size = circle.compute_size(pitch.min_loudness, pitch.max_loudness)
            color = circle.compute_color(current_time, pitch.min_frequency, pitch.max_frequency)

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

        screen.blit(dynamic_elements_surface, (0, top_area_height))
        screen.blit(static_elements_surface, (0, top_area_height))

        # Draw the FPS counter in the reserved top area
        screen.blit(fps_textbox(clock, font_size=36, color=Color.BLACK), dest=(10, 10))

        manager.update(time_delta)
        manager.draw_ui(screen)

        pygame.display.flip()

    player.stop()
    pygame.quit()


main()
