"""Text display functions for the visualiser."""
import pygame
from view.color import Color


def fps_textbox(clock: pygame.time.Clock, font_size=36, color=Color.BLACK) -> pygame.Surface:
    fps = clock.get_fps()
    font = pygame.font.SysFont(None, font_size)
    fps_text = font.render(f"{fps:.2f} FPS", True, color)
    return fps_text
