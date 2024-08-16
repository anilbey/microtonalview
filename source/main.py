import argparse
import io
import sys
import threading
import pygame

from audio_features import calculate_loudness, extract_pitch_data_frame
from view.porte import draw_frequency_lines
from dataframe_operations import (
    add_loudness,
    compute_x_positions_lazy,
    compute_y_positions_lazy,
    filter_data_by_time_window_lazy,
    get_top_k_frequency_bins,
)
from view.shape import Circle
from view.color import Color
from event import handle_quit_event, is_music_playing
from view.text_display import fps_textbox


class loading_screen:
    def __init__(self, screen, width, height, image_path):
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

    def __enter__(self):
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_buffer
        self.display_loading_screen()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout

    def display_loading_screen(self):
        self.screen.fill((255, 255, 255))  # Redraw the white background

        image_rect = self.loading_image.get_rect()
        position = (
            (self.width - image_rect.width) // 2,
            (self.height - image_rect.height) // 2,
        )

        self.screen.blit(self.loading_image, position)
        pygame.display.flip()

    def update_stdout_display(self):
        self.display_loading_screen()  # Redraw background and logo

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

        pygame.display.flip()


def main():
    parser = argparse.ArgumentParser(description="Microtonal Pitch Visualisation")

    # Add the arguments
    parser.add_argument("audio", help="Path to the .wav file")

    # Execute the parse_args() method
    args = parser.parse_args()
    # Load the audio file
    audio_file = args.audio
    icon = pygame.image.load("logo.png")
    pygame.display.set_icon(icon)

    pygame.init()
    pygame.mixer.init()
    pygame.font.init()

    # Get the display size for fullscreen mode
    display_info = pygame.display.Info()
    width, height = display_info.current_w, display_info.current_h
    screen = pygame.display.set_mode(
        (width, height), pygame.FULLSCREEN | pygame.SRCALPHA
    )
    screen.fill((255, 255, 255))  # White background
    pygame.display.set_caption("Microtonal View")

    # Create a placeholder for pitch_data
    pitch_data = None
    thread_done = False

    # Function to run in a separate thread
    def load_data():
        nonlocal pitch_data, thread_done
        print("Loading pitch data...")
        pitch_data = extract_pitch_data_frame(audio_file)
        thread_done = True

    with loading_screen(screen, width, height, "microtonal-view.png") as loader:
        # Start the loading thread
        loading_thread = threading.Thread(target=load_data)
        loading_thread.start()

        while not thread_done:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # Update the stdout display, and redraw the background and logo
            loader.update_stdout_display()

            # Control the UI refresh rate
            pygame.time.Clock().tick(30)

        # Continue after loading is complete
        print("Calculating loudness...")
        loudness = calculate_loudness(audio_file)
        loader.update_stdout_display()

        pitch_data = add_loudness(pitch_data, loudness)
        loader.update_stdout_display()

        pitch_data = pitch_data.filter(pitch_data["confidence"] > 0.5)
        loader.update_stdout_display()

        pygame.mixer.music.load(audio_file)
        loader.update_stdout_display()

    min_frequency = pitch_data["frequency"].min()
    max_frequency = pitch_data["frequency"].max()

    min_loudness = pitch_data["loudness"].min()
    max_loudness = pitch_data["loudness"].max()

    # Define padding as a percentage of the height
    padding_percent = 0.15  # 15% padding at the bottom
    padding_bottom = int(height * padding_percent)

    # Adjust scale_y to fit within the screen, considering padding
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    scale_x = width / 5

    # Create a surface for static elements
    static_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.line(
        static_elements_surface,
        Color.MID_LINE_SEPARATOR,
        (width // 2, 0),
        (width // 2, height),
        1,
    )
    top_k_freq_bins = get_top_k_frequency_bins(pitch_data, bin_size=30, k=10)
    draw_frequency_lines(
        static_elements_surface,
        top_k_freq_bins,
        height,
        min_frequency,
        max_frequency,
        padding_bottom,
    )

    # Create a separate surface for dynamic elements (circles)
    dynamic_elements_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

    running = True
    clock = pygame.time.Clock()

    circle = Circle(0, 0, 0, 0)  # the drawing circle object
    lazy_pitch_data = pitch_data.lazy()
    pygame.mixer.music.play()
    while running:
        running = handle_quit_event() and is_music_playing()

        current_time = (
            pygame.mixer.music.get_pos() / 1000.0
        )  # offset to start slightly earlier
        # Get the window frame lazily
        dataframe_window_to_display_lazy = filter_data_by_time_window_lazy(
            lazy_pitch_data, current_time
        ).with_columns(
            [
                compute_x_positions_lazy(current_time, scale_x).alias("x"),
                compute_y_positions_lazy(
                    height, padding_bottom, min_frequency, scale_y
                ).alias("y"),
            ]
        )
        dataframe_window_to_display = dataframe_window_to_display_lazy.collect()

        # Clear the dynamic elements surface each frame
        dynamic_elements_surface.fill(Color.WHITE)

        for row in dataframe_window_to_display.iter_rows(named=True):
            circle.time = row["time"]
            circle.frequency = row["frequency"]
            circle.loudness = row["loudness"]
            circle.confidence = row["confidence"]

            circle_size = circle.compute_size(min_loudness, max_loudness)
            color = circle.compute_color(current_time, min_frequency, max_frequency)

            circle_surface = pygame.Surface(
                (2 * circle_size, 2 * circle_size), pygame.SRCALPHA
            )
            pygame.draw.circle(
                circle_surface, color, (circle_size, circle_size), circle_size
            )
            dynamic_elements_surface.blit(
                circle_surface,
                (int(row["x"]) - circle_size, int(row["y"]) - circle_size),
            )

        # Draw the updated dynamic elements over the static ones
        screen.blit(dynamic_elements_surface, (0, 0))
        # Draw the static elements to the screen
        screen.blit(static_elements_surface, (0, 0))

        screen.blit(fps_textbox(clock, font_size=36, color=Color.BLACK), dest=(10, 10))

        pygame.display.flip()
        clock.tick(60)  # desired FPS

    pygame.quit()


main()
