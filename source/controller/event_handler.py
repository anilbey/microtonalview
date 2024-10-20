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
    play_pause_button: pygame_gui.elements.UIButton,
    program_state: ProgramState,
) -> ProgramState:
    """Event controller loop. Returns the updated ProgramState."""
    for event in pygame.event.get():
        ui_manager.process_events(event)
        if event.type == pygame.QUIT:
            return ProgramState.TERMINATED

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == close_button:
                return ProgramState.TERMINATED
            elif event.ui_element == minimize_button:
                pygame.display.iconify()
            elif event.ui_element == play_pause_button:
                if program_state == ProgramState.RUNNING:
                    return ProgramState.PAUSED
                elif program_state == ProgramState.PAUSED:
                    return ProgramState.RUNNING
            else:
                continue

        elif (
            event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED
            and event.ui_element == slider
        ):
            new_value = event.value
            current_time = (new_value / slider.value_range[1]) * music_length
            slider.set_current_value(new_value)
            player.seek(current_time)  # Update player's position regardless of play state

        elif event.type == pygame.KEYDOWN:
            SLIDER_STEP = 1
            if event.key == pygame.K_LEFT:
                new_value = max(
                    slider.get_current_value() - SLIDER_STEP, slider.value_range[0]
                )
                slider.set_current_value(new_value)
                current_time = (new_value / slider.value_range[1]) * music_length
                player.seek(current_time)
            elif event.key == pygame.K_RIGHT:
                new_value = min(
                    slider.get_current_value() + SLIDER_STEP, slider.value_range[1]
                )
                slider.set_current_value(new_value)
                current_time = (new_value / slider.value_range[1]) * music_length
                player.seek(current_time)
            elif event.key == pygame.K_SPACE:
                if program_state == ProgramState.RUNNING:
                    return ProgramState.PAUSED
                elif program_state == ProgramState.PAUSED:
                    return ProgramState.RUNNING
            else:
                continue
        else:
            continue

    return program_state


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
