"""PlayerView module that handles the rendering of the player scene."""

import pygame
from pathlib import Path
import pygame_gui
import polars as pl

from view.color import Color
from view.porte import draw_frequency_lines
from view.shape import Circle
from controller.program_state import ProgramState


class PlayerView:
    def __init__(
        self,
        screen: pygame.Surface,
        width: float,
        height: float,
        ui_manager: pygame_gui.UIManager,
        pitch,
        music_length: float,
        padding_percent: float = 0.15,
        top_area_height: int = 60,
    ):
        """Initialize the PlayerView."""
        self.screen = screen
        self.width = width
        self.height = height
        self.ui_manager = ui_manager
        self.pitch = pitch
        self.music_length = music_length
        self.padding_percent = padding_percent
        self.top_area_height = top_area_height
        self.usable_height = self.height - self.top_area_height
        self.padding_bottom = int(self.usable_height * self.padding_percent)
        self.scale_y = (self.usable_height - self.padding_bottom) / (
            self.pitch.max_frequency - self.pitch.min_frequency
        )
        self.scale_x = self.width / 5
        self.static_elements_surface = pygame.Surface(
            (self.width, self.usable_height), pygame.SRCALPHA
        )
        self.dynamic_elements_surface = pygame.Surface(
            (self.width, self.usable_height), pygame.SRCALPHA
        )
        self.circle = Circle(0, 0, 0, 0)

        # Initialize static elements and controls
        self.init_static_elements()
        self.init_controls()

    def init_static_elements(self):
        """Initialize static elements like frequency lines."""
        # Draw mid-line separator
        pygame.draw.line(
            self.static_elements_surface,
            Color.MID_LINE_SEPARATOR,
            (self.width // 2, 0),
            (self.width // 2, self.usable_height),
            1,
        )
        # Draw frequency lines
        draw_frequency_lines(
            self.static_elements_surface,
            self.pitch.top_k_freq_bins,
            self.usable_height,
            self.pitch.min_frequency,
            self.pitch.max_frequency,
            self.padding_bottom,
        )

    def init_controls(self):
        """Initialize playback controls."""
        # Load images
        play_image = pygame.image.load(Path("static") / "play_icon.png").convert_alpha()
        pause_image = pygame.image.load(Path("static") / "pause_icon.png").convert_alpha()

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

        # Create play/pause button
        self.play_pause_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((20, button_y), button_size),
            text="",
            manager=self.ui_manager,
            object_id="#play_pause_button",
        )
        self.play_pause_button.set_image(pause_image)
        self.pause_image = pause_image
        self.play_image = play_image

        # Create slider
        self.slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(
                (70, slider_y), (self.width - 90, slider_height)
            ),
            start_value=0,
            value_range=(0, self.music_length),
            manager=self.ui_manager,
            object_id="#slider",
        )

    def update_controls(self, current_time: float, program_state):
        """Update the controls based on current time and program state."""
        # Update slider based on current_time
        self.slider.set_current_value(current_time)

        # Update play/pause button image
        if program_state == ProgramState.RUNNING:
            self.play_pause_button.set_image(self.pause_image)
        elif program_state == ProgramState.PAUSED:
            self.play_pause_button.set_image(self.play_image)

    def update_dynamic_elements(
        self, dataframe_window_to_display: pl.DataFrame, current_time: float
    ):
        """Update dynamic elements based on current data."""
        self.screen.fill(Color.WHITE)
        self.dynamic_elements_surface.fill(
            (0, 0, 0, 0)
        )  # Clear dynamic surface with transparent fill
        for row in dataframe_window_to_display.iter_rows(named=True):
            self.circle.time = row["time"]
            self.circle.frequency = row["frequency"]
            self.circle.loudness = row["loudness"]
            self.circle.confidence = row["confidence"]

            circle_size = self.circle.compute_size(
                self.pitch.min_loudness, self.pitch.max_loudness
            )
            color = self.circle.compute_color(
                current_time, self.pitch.min_frequency, self.pitch.max_frequency
            )

            circle_surface = pygame.Surface(
                (2 * circle_size, 2 * circle_size), pygame.SRCALPHA
            )
            pygame.draw.circle(
                circle_surface, color, (circle_size, circle_size), circle_size
            )
            self.dynamic_elements_surface.blit(
                circle_surface,
                (int(row["x"]) - circle_size, int(row["y"]) - circle_size),
            )

    def render(self):
        """Render the current frame to the screen."""
        # Blit dynamic and static surfaces onto the main screen
        self.screen.blit(self.dynamic_elements_surface, (0, self.top_area_height))
        self.screen.blit(self.static_elements_surface, (0, self.top_area_height))
