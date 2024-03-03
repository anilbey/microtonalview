import argparse
import colorsys
import numpy as np
import pygame
import polars as pl


# Custom function to map frequency to color
def frequency_to_color(frequency, min_freq, max_freq):
    # Normalize frequency value
    normalized_value = (frequency - min_freq) / (max_freq - min_freq)
    # Apply a non-linear transformation to make changes more sensitive
    normalized_value = pow(normalized_value, 0.4)

    # Use HSV color space for more vibrant colors
    # Hue varies from 0 to 1, corresponding to the full range of colors
    hue = normalized_value
    saturation = 0.9  # High saturation for more vivid colors
    value = 0.9       # High value for brightness

    # Convert HSV to RGB
    rgb = colorsys.hsv_to_rgb(hue, saturation, value)
    # Scale RGB values to 0-255 range
    return tuple(int(i * 255) for i in rgb)



def blend_color(base_color, confidence):
    # Apply alpha based on confidence to the base color
    alpha = int(255 * confidence)
    return base_color + (alpha,)


def loudness_to_size(loudness, min_loudness, max_loudness):
    normalized_loudness = (loudness - min_loudness) / (max_loudness - min_loudness)
    res = max(1, int(normalized_loudness * 10))  # Scale and ensure minimum size of 1
    return res * 2.5  # Scale up to make circles bigger


def calculate_frequency_bins(df, bin_size):
    """Calculate the frequency bin usage."""
    min_freq = df["frequency"].min()
    max_freq = df["frequency"].max()
    bins = np.arange(min_freq, max_freq, bin_size)
    freq_counts, _ = np.histogram(df["frequency"], bins)
    return freq_counts, bins

def get_top_k_frequency_bins(data, bin_size, k):
    # Calculate frequency bins
    freq_counts, bins = calculate_frequency_bins(data, bin_size)

    # Create a DataFrame for frequency bin data
    bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]
    freq_df = pl.DataFrame({
        "Frequency Range": bin_labels,
        "Count": freq_counts
    })

    # Get top k frequency bins
    top_k_freq_bins = freq_df.top_k(k, by="Count")
    return top_k_freq_bins


def get_note_mapping():
    # Mapping of note names to frequencies
    notes = ["C#2/Db2", "D2", "D#2/Eb2", "E2", "F2", "F#2/Gb2", "G2", "G#2/Ab2", "A2", "A#2/Bb2", "B2",
             "C3", "C#3/Db3", "D3", "D#3/Eb3", "E3", "F3", "F#3/Gb3", "G3", "G#3/Ab3", "A3", "A#3/Bb3", "B3",
             "C4", "C#4/Db4", "D4", "D#4/Eb4", "E4", "F4", "F#4/Gb4", "G4", "G#4/Ab4", "A4", "A#4/Bb4", "B4",
             "C5", "C#5/Db5", "D5", "D#5/Eb5", "E5", "F5", "F#5/Gb5", "G5", "G#5/Ab5", "A5", "A#5/Bb5", "B5",
             "C6", "C#6/Db6", "D6"]
    frequencies = [69.30, 73.42, 77.78, 82.41, 87.31, 92.50, 98.00, 103.83, 110.00, 116.54, 123.47,
                   130.81, 138.59, 146.83, 155.56, 164.81, 174.61, 185.00, 196.00, 207.65, 220.00, 233.08, 246.94,
                   261.63, 277.18, 293.66, 311.13, 329.63, 349.23, 369.99, 392.00, 415.30, 440.00, 466.16, 493.88,
                   523.25, 554.37, 587.33, 622.25, 659.25, 698.46, 739.99, 783.99, 830.61, 880.00, 932.33, 987.77,
                   1046.50, 1108.73, 1174.66]
    return dict(zip(frequencies, notes))


def find_closest_note(freq, note_mapping):
    # Find the closest note for the given frequency
    closest_freq = min(note_mapping.keys(), key=lambda k: abs(k - freq))
    return note_mapping[closest_freq]


def draw_text_with_outline(screen, font, text, x, y, main_color, outline_color, outline_width):
    # Render the outline
    outline_surf = font.render(text, True, outline_color)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:  # Offset for the outline
                screen.blit(outline_surf, (x + dx, y + dy))

    # Render the main text on top
    text_surf = font.render(text, True, main_color)
    screen.blit(text_surf, (x, y))


def draw_frequency_lines(screen, top_k_freq_bins, height, min_frequency, max_frequency, padding_bottom, note_mapping):
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    font = pygame.font.SysFont(None, 24)
    main_color = (0, 0, 0)           # Black text
    outline_color = (252, 251, 237)  # White outline
    outline_width = 4

    for row in top_k_freq_bins.iter_rows(named=True):
        avg_freq = (float(row["Frequency Range"].split('-')[0]) + float(row["Frequency Range"].split('-')[1])) / 2
        closest_note = find_closest_note(avg_freq, note_mapping)
        y = (height - padding_bottom) - (avg_freq - min_frequency) * scale_y

        # Draw line
        pygame.draw.line(screen, (178, 162, 167), (0, y), (screen.get_width(), y), 1)

        # Draw text with outline
        draw_text_with_outline(screen, font, closest_note, 5, int(y) - 15, main_color, outline_color, outline_width)


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")

    # Add the arguments
    parser.add_argument("features", help="The features csv for rendering")
    parser.add_argument("audio", help="Path to the .wav file")

    # Execute the parse_args() method
    args = parser.parse_args()

    icon = pygame.image.load('logo.png')
    pygame.display.set_icon(icon)

    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    width, height = 1920, 1080
    screen = pygame.display.set_mode((width, height), pygame.SRCALPHA)
    pygame.display.set_caption("Microtonal Pitch Visualisation")

    # Use Polars to load data from the features CSV file
    data = pl.read_csv(args.features)

    note_mapping = get_note_mapping()
    top_k_freq_bins = get_top_k_frequency_bins(data, bin_size=30, k=10)
    # Load the audio file
    audio_file = args.audio
    pygame.mixer.music.load(audio_file)

    min_frequency = data["frequency"].min()
    max_frequency = data["frequency"].max()

    min_loudness = data["loudness"].min()
    max_loudness = data["loudness"].max()

    # Define padding as a percentage of the height
    padding_percent = 0.15  # 15% padding at the bottom
    padding_bottom = int(height * padding_percent)

    # Adjust scale_y to fit within the screen, considering padding
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    scale_x = width / 5

    font = pygame.font.SysFont(None, 36)
    pygame.mixer.music.play()

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        current_time = pygame.mixer.music.get_pos() / 1000.0
        # Use Polars for data filtering
        relevant_data = data.filter(
            (data["time"] >= current_time - 2.5) & (data["time"] <= current_time + 2.5)
        )

        screen.fill((255, 255, 255))

        for row in relevant_data.iter_rows(named=True):
            x = (row["time"] - current_time + 2.5) * scale_x
            y = (height - padding_bottom) - (row["frequency"] - min_frequency) * scale_y
            circle_size = loudness_to_size(row["loudness"], min_loudness, max_loudness)

            is_current_circle = (
                abs(row["time"] - current_time) < 0.01
            )  # Adjust the threshold as needed

            if is_current_circle:
                # Make the current circle red
                color = (255, 0, 0)
            else:
                base_color = frequency_to_color(
                    row["frequency"], min_frequency, max_frequency
                )
                color = blend_color(base_color, row["confidence"])

            circle_surface = pygame.Surface(
                (2 * circle_size, 2 * circle_size), pygame.SRCALPHA
            )
            pygame.draw.circle(
                circle_surface, color, (circle_size, circle_size), circle_size
            )
            screen.blit(circle_surface, (int(x) - circle_size, int(y) - circle_size))

        # Draw lines and text for top k frequencies
        # This is done after drawing the circles to ensure text is on top
        draw_frequency_lines(screen, top_k_freq_bins, height, min_frequency, max_frequency, padding_bottom, note_mapping)

        pygame.draw.line(
            screen, (255, 153, 51), (width // 2, 0), (width // 2, height), 1
        )
        fps = clock.get_fps()
        fps_text = font.render(f"{fps:.2f} FPS", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)  # desired FPS

        # Check if music is still playing
        if not pygame.mixer.music.get_busy():
            running = False

    pygame.quit()


main()
