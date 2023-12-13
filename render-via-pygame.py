import pygame
import pandas as pd


# Custom function to map frequency to color
def frequency_to_color(frequency, min_freq, max_freq):
    # Normalize frequency value
    value = (frequency - min_freq) / (max_freq - min_freq)
    # Apply a non-linear transformation to make changes more sensitive
    value = pow(value, 0.4)
    # Generate color using a more sensitive scale
    return (int(255 * value), 0, int(255 * (1 - value)))


def blend_color(base_color, confidence):
    # Apply alpha based on confidence to the base color
    alpha = int(255 * confidence)
    return base_color + (alpha,)


def main():
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    width, height = 1920, 1080
    screen = pygame.display.set_mode((width, height), pygame.SRCALPHA)
    pygame.display.set_caption("Real-Time Pitch Visualization")

    data = pd.read_csv("tunar-hüzzam.f0.csv", dtype=float)
    audio_file = "tunar-hüzzam.wav"
    pygame.mixer.music.load(audio_file)

    min_frequency = data["frequency"].min()
    max_frequency = data["frequency"].max()

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
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        current_time = pygame.mixer.music.get_pos() / 1000.0
        relevant_data = data[
            (data["time"] >= current_time - 2.5) & (data["time"] <= current_time + 2.5)
        ]

        screen.fill((255, 255, 255))
        for _, row in relevant_data.iterrows():
            x = (row["time"] - current_time + 2.5) * scale_x
            y = (height - padding_bottom) - (row["frequency"] - min_frequency) * scale_y
            base_color = frequency_to_color(
                row["frequency"], min_frequency, max_frequency
            )
            color = blend_color(base_color, row["confidence"])

            circle_surface = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, color, (3, 3), 3)
            screen.blit(circle_surface, (int(x) - 3, int(y) - 3))

        pygame.draw.line(screen, (255, 0, 0), (width // 2, 0), (width // 2, height), 2)
        fps = clock.get_fps()
        fps_text = font.render(f"{fps:.2f} FPS", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


main()
