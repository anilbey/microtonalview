"""Module responsible of drawing the porte."""

from functools import lru_cache
import json
from pathlib import Path
from types import MappingProxyType
import pygame

from view.color import RGBA, Color


static_data_dir = Path(__file__).parent.parent / "static"


@lru_cache(maxsize=1)
def get_note_mapping() -> MappingProxyType[float, str]:
    """Get the note mapping for frequencies."""
    with open(static_data_dir / "note_mapping.json") as f:
        note_mapping = json.load(f)
    note_mapping = {float(k): v for k, v in note_mapping.items()}
    return MappingProxyType(note_mapping)


def find_closest_note(freq: float) -> str:
    """Find the closest note for the given frequency."""
    note_mapping = get_note_mapping()
    closest_freq = min(note_mapping.keys(), key=lambda k: abs(k - freq))
    return note_mapping[closest_freq]


def draw_text_with_outline(
    screen, font, text, x, y, main_color: RGBA, outline_color: RGBA, outline_width
):
    # Render the outline
    outline_surf = font.render(text, True, outline_color)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:  # Offset for the outline
                screen.blit(outline_surf, (x + dx, y + dy))

    # Render the main text on top
    text_surf = font.render(text, True, main_color)
    screen.blit(text_surf, (x, y))


def draw_frequency_lines(
    screen, top_k_freq_bins, height, min_frequency, max_frequency, padding_bottom
):
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    font = pygame.font.SysFont(None, 24)
    outline_width = 4

    for row in top_k_freq_bins.iter_rows(named=True):
        avg_freq = (
            float(row["Frequency Range"].split("-")[0])
            + float(row["Frequency Range"].split("-")[1])
        ) / 2
        closest_note = find_closest_note(avg_freq)
        y = (height - padding_bottom) - (avg_freq - min_frequency) * scale_y

        # Draw line
        pygame.draw.line(screen, Color.PORTE_LINE, (0, y), (screen.get_width(), y), 1)

        # Draw text with outline
        draw_text_with_outline(
            screen,
            font,
            closest_note,
            5,
            int(y) - 15,
            Color.NOTE_TEXT,
            Color.PORTE_OUTLINE,
            outline_width,
        )
