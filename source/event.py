"""Event handlers."""
import pygame


def handle_quit_event() -> bool:
    """Check if the user has quit the application."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    return True


def is_music_playing() -> bool:
    """Check if music is playing."""
    return pygame.mixer.music.get_busy()
