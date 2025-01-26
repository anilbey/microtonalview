import argparse
from pathlib import Path
import pygame
import pygame_gui
from controller.scene_manager import SceneManager
from controller.program_state import ProgramState


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")
    parser.add_argument("audio", nargs='?', help="Path to the .wav file (optional)")
    args = parser.parse_args()
    audio_file: str | None = args.audio

    icon = pygame.image.load(Path("assets") / "logo.png")
    pygame.display.set_icon(icon)

    pygame.init()
    pygame.font.init()

    # Get the display size for fullscreen mode
    display_info = pygame.display.Info()
    width, height = display_info.current_w, display_info.current_h
    screen = pygame.display.set_mode(
        (width, height), pygame.FULLSCREEN | pygame.SRCALPHA
    )
    pygame.display.set_caption("Microtonal View")

    # Initialize pygame_gui
    ui_manager = pygame_gui.UIManager((width, height))

    # SceneManager manages the loading of pitch data
    scene_manager = SceneManager(screen, width, height, ui_manager)
    program_state = ProgramState.MENU
    while program_state != ProgramState.TERMINATED:
        if audio_file is None:
            audio_file = scene_manager.display_menu()
        pitch = scene_manager.display_loading_screen(audio_file)
        program_state = scene_manager.display_player(pitch, audio_file)


if __name__ == "__main__":
    main()
