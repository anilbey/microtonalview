"""Manages the switching of scenes."""

from concurrent.futures import ThreadPoolExecutor
import polars as pl
import pygame
import pygame_gui
from pydub import AudioSegment

from audio_features import extract_pitch_data_frame
from caching import hash_file, load_from_cache, save_to_cache
from controller.event_handler import handle_loading_screen_events, handle_visualiser_events
from controller.program_state import ProgramState
from dataframe_operations import (
    process_pitch_data,
    compute_x_positions_lazy,
    compute_y_positions_lazy,
    filter_data_by_time_window_lazy,
)
from model import Pitch
from view.loading_screen import loading_screen
from view.porte import draw_frequency_lines
from view.shape import Circle
from view.color import Color
from view.text_display import fps_textbox
from controller.audio_player import AudioPlayer


class HeaderWidgets:
    width: float
    ui_manager: pygame_gui.UIManager
    close_button: pygame_gui.elements.UIButton
    minimize_button: pygame_gui.elements.UIButton

    def __init__(self, width: float, ui_manager: pygame_gui.UIManager):
        """Initialize close and minimize buttons."""
        self.width = width
        self.ui_manager = ui_manager
        self.close_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((int(width) - 45, 10), (35, 35)),
            text="X",
            manager=ui_manager,
            object_id="#close_button",
        )
        self.minimize_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((int(width) - 85, 10), (35, 35)),
            text="-",
            manager=ui_manager,
            object_id="#minimize_button",
        )


class SceneManager:
    screen: pygame.Surface
    width: float
    height: float
    ui_manager: pygame_gui.UIManager
    header_widgets: HeaderWidgets

    def __init__(
        self,
        screen: pygame.Surface,
        width: float,
        height: float,
        ui_manager: pygame_gui.UIManager,
    ):
        """Initialize the scene manager and load header widgets."""
        self.screen = screen
        self.width = width
        self.height = height
        self.ui_manager = ui_manager
        self.header_widgets = HeaderWidgets(width, ui_manager)

    def display_loading_screen(self, audio_file: str) -> Pitch:
        """Display the loading screen and process the pitch data."""
        with loading_screen(
            self.screen, int(self.width), int(self.height), "microtonal-view.png"
        ) as loader:
            audio_hash: str = hash_file(audio_file)
            cached_data: pl.DataFrame | None = load_from_cache(audio_hash)

            with ThreadPoolExecutor(max_workers=2) as executor:
                if cached_data is not None:
                    raw_pitch_data = cached_data
                    print("Using cached data...")
                else:
                    future = executor.submit(extract_pitch_data_frame, audio_file)
                    print("Extracting pitch data...")

                    # Frame loop: extract pitch data
                    while not future.done():
                        handle_loading_screen_events(
                            self.ui_manager,
                            self.header_widgets.close_button,
                            self.header_widgets.minimize_button,
                        )
                        loader.display_loading_screen()
                        loader.update_stdout_display()
                        self.ui_manager.update(0.01)
                        self.ui_manager.draw_ui(self.screen)
                        pygame.display.flip()
                        pygame.time.Clock().tick(20)

                    raw_pitch_data = future.result()
                    save_to_cache(audio_hash, raw_pitch_data)

                print("Processing pitch data...")
                future_process = executor.submit(
                    process_pitch_data, raw_pitch_data, audio_file
                )

                # Frame loop: process pitch data
                while not future_process.done():
                    handle_loading_screen_events(
                        self.ui_manager,
                        self.header_widgets.close_button,
                        self.header_widgets.minimize_button,
                    )
                    loader.display_loading_screen()
                    loader.update_stdout_display()
                    self.ui_manager.update(0.01)
                    self.ui_manager.draw_ui(self.screen)
                    pygame.display.flip()
                    pygame.time.Clock().tick(20)

                pitch = future_process.result()

        return pitch

    def display_player(self, pitch: Pitch, audio_file: str) -> ProgramState:
        """Display the player scene and handle the main loop."""
        # Initialize necessary variables
        top_area_height = 60  # Height reserved for buttons and FPS display
        usable_height = self.height - top_area_height  # Height available for the rest of the program

        padding_percent = 0.15
        padding_bottom = int(usable_height * padding_percent)

        scale_y = (usable_height - padding_bottom) / (pitch.max_frequency - pitch.min_frequency)
        scale_x = self.width / 5

        # Create surfaces for static and dynamic elements
        static_elements_surface = pygame.Surface((self.width, usable_height), pygame.SRCALPHA)
        pygame.draw.line(
            static_elements_surface,
            Color.MID_LINE_SEPARATOR,
            (self.width // 2, 0),
            (self.width // 2, usable_height),
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

        dynamic_elements_surface = pygame.Surface((self.width, usable_height), pygame.SRCALPHA)

        program_state = ProgramState.RUNNING
        clock = pygame.time.Clock()

        circle = Circle(0, 0, 0, 0)
        lazy_pitch_data = pitch.annotated_pitch_data_frame.lazy()

        audio_segment = AudioSegment.from_wav(audio_file)
        player = AudioPlayer(audio_segment)

        play_image = pygame.image.load('play_icon.png').convert_alpha()
        pause_image = pygame.image.load('pause_icon.png').convert_alpha()

        # Resize images if necessary to fit the button size
        button_size = (40, 40)
        play_image = pygame.transform.smoothscale(play_image, button_size)
        pause_image = pygame.transform.smoothscale(pause_image, button_size)

        # Define control area dimensions
        control_area_height = 60
        control_area_y = self.height - control_area_height

        # Center controls vertically within control area
        button_y = control_area_y + (control_area_height - button_size[1]) // 2
        slider_height = 40
        slider_y = control_area_y + (control_area_height - slider_height) // 2

        play_pause_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((20, button_y), button_size),
            text='',
            manager=self.ui_manager,
            object_id="#play_pause_button",
        )
        play_pause_button.set_image(pause_image)

        slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((70, slider_y), (self.width - 90, slider_height)),
            start_value=0,
            value_range=(0, 64),
            manager=self.ui_manager,
            object_id="#slider",
        )

        music_length = len(audio_segment) / 1000.0  # in seconds

        player.play()  # Start playback

        # Main loop
        while program_state != ProgramState.TERMINATED:
            time_delta = clock.tick(60) / 1000.0

            program_state = handle_visualiser_events(
                self.ui_manager,
                self.header_widgets.close_button,
                self.header_widgets.minimize_button,
                player,
                slider,
                music_length,
                play_pause_button,
                program_state
            )
            if program_state == ProgramState.RUNNING:
                play_pause_button.set_image(pause_image)
            elif program_state == ProgramState.PAUSED:
                play_pause_button.set_image(play_image)

            current_time = player.get_elapsed_time()

            # Update slider based on current_time
            slider_percentage = (current_time / music_length) * slider.value_range[1]
            slider.set_current_value(slider_percentage)

            # Update visuals based on current_time
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

            # Handle playback
            if program_state == ProgramState.RUNNING:
                if not player.is_playing():
                    player.play(start_time=current_time)
            elif program_state == ProgramState.PAUSED:
                if player.is_playing():
                    player.pause()

            # Clear the screen with white color (including the top area)
            self.screen.fill(Color.WHITE)

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

            self.screen.blit(dynamic_elements_surface, (0, top_area_height))
            self.screen.blit(static_elements_surface, (0, top_area_height))

            # Draw the FPS counter in the reserved top area
            self.screen.blit(fps_textbox(clock, font_size=36, color=Color.BLACK), dest=(10, 10))

            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.screen)

            pygame.display.flip()

        return program_state
