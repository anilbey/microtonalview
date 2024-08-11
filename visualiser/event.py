"""Event handlers."""
import pygame


def handle_quit_event():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    return True
