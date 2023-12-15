import argparse
import random
import pygame
import polars as pl


# Custom function to map frequency to color
def frequency_to_color(frequency, min_freq, max_freq):
    # Normalize frequency value
    value = (frequency - min_freq) / (max_freq - min_freq)
    # Apply a non-linear transformation to make changes more sensitive
    value = pow(value, 0.4)
    # Generate color using a more sensitive scale
    return (int(255 * value), 155, int(255 * (1 - value)))


def blend_color(base_color, confidence):
    # Apply alpha based on confidence to the base color
    alpha = int(255 * confidence)
    return base_color + (alpha,)


def loudness_to_size(loudness, min_loudness, max_loudness):
    normalized_loudness = (loudness - min_loudness) / (max_loudness - min_loudness)
    return max(1, int(normalized_loudness * 10))  # Scale and ensure minimum size of 1


def main():

    parser = argparse.ArgumentParser(description="Real-Time Pitch Visualization")

    # Add the arguments
    parser.add_argument('name', metavar='name', type=str, help='the name of the song')

    # Execute the parse_args() method
    args = parser.parse_args()

    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    width, height = 1920, 1080
    screen = pygame.display.set_mode((width, height), pygame.SRCALPHA)
    pygame.display.set_caption("Real-Time Pitch Visualization")

    # Use Polars to load data
    data = pl.read_csv(f"{args.name}-loudness.csv")
    audio_file = f"{args.name}.wav"
    pygame.mixer.music.load(audio_file)

    min_frequency = data["frequency"].min()
    max_frequency = data["frequency"].max()

    min_loudness = data["loudness"].min()
    max_loudness = data["loudness"].max()

    # Define padding as a percentage of the height
    padding_percent = 0.25  # 10% padding at the bottom
    padding_bottom = int(height * padding_percent)

    # Adjust scale_y to fit within the screen, considering padding
    scale_y = (height - padding_bottom) / (max_frequency - min_frequency)
    scale_x = width / 5

    font = pygame.font.SysFont(None, 36)
    pygame.mixer.music.play()

    running = True
    clock = pygame.time.Clock()

    particles = []

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        current_time = pygame.mixer.music.get_pos() / 1000.0
        # Use Polars for data filtering
        relevant_data = data.filter(
            (data["time"] >= current_time - 2.5) & 
            (data["time"] <= current_time + 2.5)
        )

        screen.fill((255, 255, 255))

        # Update and draw particles
        for particle in particles[:]:
            particle.update()
            particle.draw(screen)
            if particle.life <= 0:
                particles.remove(particle)

        for row in relevant_data.iter_rows(named=True):
            x = (row["time"] - current_time + 2.5) * scale_x
            y = (height - padding_bottom) - (row["frequency"] - min_frequency) * scale_y
            circle_size = loudness_to_size(row["loudness"], min_loudness, max_loudness)

            is_current_circle = abs(row["time"] - current_time) < 0.01  # Adjust the threshold as needed

            if is_current_circle:
                # Make the current circle red
                color = (225, 0, 0)
            else:
                base_color = frequency_to_color(row["frequency"], min_frequency, max_frequency)
                color = blend_color(base_color, row["confidence"])

            circle_surface = pygame.Surface((2 * circle_size, 2 * circle_size), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, color, (circle_size, circle_size), circle_size)
            screen.blit(circle_surface, (int(x) - circle_size, int(y) - circle_size))


        pygame.draw.line(screen, (255, 153, 51), (width // 2, 0), (width // 2, height), 1)
        fps = clock.get_fps()
        fps_text = font.render(f"{fps:.2f} FPS", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


main()
