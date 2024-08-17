"""Event handlers."""
import pygame


def is_music_playing() -> bool:
    """Check if music is playing."""
    return pygame.mixer.music.get_busy()
