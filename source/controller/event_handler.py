"""Manager event handling."""

import pygame
import pygame_gui

from controller.audio_player import AudioPlayer
from controller.program_state import ProgramState


def handle_visualiser_events(
    ui_manager: pygame_gui.UIManager,
    close_button: pygame_gui.elements.UIButton,
    minimize_button: pygame_gui.elements.UIButton,
    player: AudioPlayer,
    slider: pygame_gui.elements.UIHorizontalSlider,
    music_length: float,
) -> ProgramState:
    """Event controller loop. Returns the ProgramState."""
    for event in pygame.event.get():
        ui_manager.process_events(event)
        if event.type == pygame.QUIT:
            return ProgramState.TERMINATED
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == close_button:
                return ProgramState.TERMINATED
            elif event.ui_element == minimize_button:
                pygame.display.iconify()
            else:
                continue
        elif (
            event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED
            and event.ui_element == slider
        ):
            current_time = (event.value / slider.value_range[1]) * music_length
            player.play(start_time=current_time)  # Restart music at new time
        elif event.type == pygame.KEYDOWN:
            SLIDER_STEP = 1
            if event.key == pygame.K_LEFT:
                new_value = max(
                    slider.get_current_value() - SLIDER_STEP, slider.value_range[0]
                )
                slider.set_current_value(new_value)
            elif event.key == pygame.K_RIGHT:
                new_value = min(
                    slider.get_current_value() + SLIDER_STEP, slider.value_range[1]
                )
                slider.set_current_value(new_value)
            else:
                continue
            current_time = (new_value / slider.value_range[1]) * music_length
            player.play(start_time=current_time)
        else:
            continue

    return ProgramState.RUNNING


def handle_loading_screen_events(
    ui_manager: pygame_gui.UIManager,
    close_button: pygame_gui.elements.UIButton,
    minimize_button: pygame_gui.elements.UIButton
) -> None:
    """Event handler for the loading screen with future cancellation."""
    for event in pygame.event.get():
        ui_manager.process_events(event)
        if event.type == pygame.QUIT:
            pygame.quit()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == close_button:
                pygame.quit()
            elif event.ui_element == minimize_button:
                pygame.display.iconify()
            else:
                continue
        else:
            continue
