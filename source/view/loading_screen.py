"""Rendering for the loading screen module."""

import io
from pathlib import Path
import sys
from typing import Self
import pygame


class loading_screen:
    """Context manager that displays the loading screen."""

    def __init__(
        self, screen: pygame.Surface, width: int, height: int, image_path: Path
    ) -> None:
        self.screen = screen
        self.width = width
        self.height = height
        self.image_path = image_path
        self.font = pygame.font.Font(None, 36)
        self.rect_color = (50, 50, 50)
        self.text_color = (255, 255, 255)
        self.rect_height = 150
        self.stdout_buffer = io.StringIO()
        self.loading_image = pygame.image.load(self.image_path)

    def __enter__(self) -> Self:
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_buffer
        self.render_loading_screen()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout

    def render_loading_screen(self) -> None:
        self.screen.fill((255, 255, 255))  # Redraw the white background

        image_rect = self.loading_image.get_rect()
        position = (
            (self.width - image_rect.width) // 2,
            (self.height - image_rect.height) // 2,
        )

        self.screen.blit(self.loading_image, position)

    def update_stdout_display(self) -> None:
        """Updates the stdout display element."""
        stdout_content = self.stdout_buffer.getvalue()
        lines = stdout_content.splitlines()
        max_lines = self.rect_height // self.font.get_height()
        lines_to_display = lines[-max_lines:]

        rect = pygame.Rect(
            0, self.height - self.rect_height, self.width, self.rect_height
        )
        pygame.draw.rect(self.screen, self.rect_color, rect)

        for i, line in enumerate(lines_to_display):
            text_surface = self.font.render(line, True, self.text_color)
            self.screen.blit(
                text_surface,
                (10, self.height - self.rect_height + i * self.font.get_height()),
            )
