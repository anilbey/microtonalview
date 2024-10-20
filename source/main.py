import argparse
from pathlib import Path
import pygame
import pygame_gui
from controller.scene_manager import SceneManager


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")
    parser.add_argument("audio", help="Path to the .wav file")
    args = parser.parse_args()
    audio_file = args.audio

    icon = pygame.image.load(Path("static") / "logo.png")
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
    pitch = scene_manager.display_loading_screen(audio_file)

    # Now call display_player
    scene_manager.display_player(pitch, audio_file)


if __name__ == "__main__":
    main()
