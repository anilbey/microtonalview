"""Manages the switching of scenes."""

from concurrent.futures import ThreadPoolExecutor
import polars as pl
import pygame
import pygame_gui

from audio_features import extract_pitch_data_frame
from caching import hash_file, load_from_cache, save_to_cache
from controller.event_handler import handle_loading_screen_events
from dataframe_operations import process_pitch_data
from model import Pitch
from view.loading_screen import loading_screen


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
