"""Manages the switching of scenes."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import polars as pl
import pygame
import pygame_gui
from pydub import AudioSegment

from audio_features import extract_pitch_data_frame
from caching import hash_file, load_from_cache, save_to_cache
from controller.event_handler import handle_header_events, handle_visualiser_events
from controller.program_state import ProgramState
from dataframe_operations import (
    process_pitch_data,
    compute_x_positions_lazy,
    compute_y_positions_lazy,
    filter_data_by_time_window_lazy,
)
from model import Pitch
from view.player import PlayerView
from view.loading_screen import loading_screen
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

    def display_menu(self) -> str | None:
        """Display the main menu and return the selected audio file path."""
        logo_image = pygame.image.load(Path("assets") / "microtonal-view.png")
        logo_rect = logo_image.get_rect(center=(self.width/2, self.height/3))

        load_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.width/2 - 150, self.height/2), (300, 80)),
            text="Load a WAV file",
            manager=self.ui_manager,
        )

        file_dialog: pygame_gui.windows.UIFileDialog | None = None
        selected_file: str | None = None
        program_running = True
        clock = pygame.time.Clock()

        while program_running:
            time_delta = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.ui_manager.process_events(event)
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.header_widgets.close_button:
                        pygame.quit()
                    elif event.ui_element == self.header_widgets.minimize_button:
                        pygame.display.iconify()
                    elif event.ui_element == load_button:
                        file_dialog = pygame_gui.windows.UIFileDialog(
                            rect=pygame.Rect(0, 0, 800, 600),
                            manager=self.ui_manager,
                            window_title="Open Audio File",
                            initial_file_path=str(Path.home()),
                            allow_picking_directories=False,
                            allowed_suffixes={".wav"}
                        )
                if event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                    if event.ui_element == file_dialog:
                        selected_file = event.text
                        program_running = False

            self.ui_manager.update(time_delta)
            self.screen.fill((255, 255, 255))
            self.screen.blit(logo_image, logo_rect)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

        load_button.kill()
        if file_dialog:
            file_dialog.kill()

        return selected_file

    def display_loading_screen(self, audio_file: str) -> Pitch:
        """Display the loading screen and process the pitch data."""
        with loading_screen(
            self.screen, int(self.width), int(self.height), Path("assets") / "microtonal-view.png"
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
                        handle_header_events(
                            self.ui_manager,
                            self.header_widgets.close_button,
                            self.header_widgets.minimize_button,
                        )
                        loader.render_loading_screen()
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
                    handle_header_events(
                        self.ui_manager,
                        self.header_widgets.close_button,
                        self.header_widgets.minimize_button,
                    )
                    loader.render_loading_screen()
                    loader.update_stdout_display()
                    self.ui_manager.update(0.01)
                    self.ui_manager.draw_ui(self.screen)
                    pygame.display.flip()
                    pygame.time.Clock().tick(20)

                pitch = future_process.result()

        return pitch

    def display_player(self, pitch: Pitch, audio_file: str) -> ProgramState:
        """Display the player scene and handle the main loop."""
        # Initialize audio player
        audio_segment = AudioSegment.from_wav(audio_file)
        player = AudioPlayer(audio_segment)
        player.play()  # Start playback

        # Get music length in seconds
        music_length = len(audio_segment) / 1000.0

        player_view = PlayerView(
            self.screen,
            self.width,
            self.height,
            self.ui_manager,
            pitch,
            music_length,
        )

        program_state = ProgramState.PLAYING
        clock = pygame.time.Clock()

        lazy_pitch_data = pitch.annotated_pitch_data_frame.lazy()

        # Main loop
        while program_state != ProgramState.TERMINATED:
            time_delta = clock.tick(30) / 1000.0

            program_state = handle_visualiser_events(
                self.ui_manager,
                self.header_widgets.close_button,
                self.header_widgets.minimize_button,
                player,
                player_view.slider,
                music_length,
                player_view.play_pause_button,
                program_state,
            )

            current_time = player.get_elapsed_time()

            player_view.update_controls(current_time, program_state)

            # Update visuals based on current_time
            dataframe_window_to_display_lazy = filter_data_by_time_window_lazy(
                lazy_pitch_data, current_time
            ).with_columns(
                [
                    compute_x_positions_lazy(current_time, player_view.scale_x).alias("x"),
                    compute_y_positions_lazy(
                        player_view.usable_height,
                        player_view.padding_bottom,
                        pitch.min_frequency,
                        player_view.scale_y,
                    ).alias("y"),
                ]
            )
            dataframe_window_to_display = dataframe_window_to_display_lazy.collect()

            # Handle playback
            if program_state == ProgramState.PLAYING:
                if not player.is_playing():
                    player.play(start_time=current_time)
            elif program_state == ProgramState.PAUSED:
                if player.is_playing():
                    player.pause()

            player_view.update_dynamic_elements(dataframe_window_to_display, current_time)
            player_view.render()
            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.screen)

            pygame.display.flip()

        return program_state
