import pygame
import pandas as pd


# Custom function to map frequency to color
def frequency_to_color(frequency, min_freq, max_freq):
    # Normalize frequency value
    value = (frequency - min_freq) / (max_freq - min_freq)

    # Simple linear interpolation between blue (low freq) and red (high freq)
    return (int(255 * value), 0, int(255 * (1 - value)))


# Initialize Pygame and its mixer
pygame.init()
pygame.mixer.init()
pygame.font.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Real-Time Pitch Visualization")

# Load data
data = pd.read_csv("tunar-hüzzam.f0.csv", dtype=float)

# Load audio
audio_file = "tunar-hüzzam.wav"
pygame.mixer.music.load(audio_file)

# Visualization parameters
min_frequency = data["frequency"].min()
max_frequency = data["frequency"].max()

# Preprocess the data for efficient access
data["color"] = data["frequency"].apply(
    lambda f: frequency_to_color(f, min_frequency, max_frequency)
)

scale_y = height / (max_frequency - min_frequency)
scale_x = width / 5

# Font for FPS display
font = pygame.font.SysFont(None, 36)

# Play audio
pygame.mixer.music.play()

running = True
clock = pygame.time.Clock()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    current_time = pygame.mixer.music.get_pos() / 1000.0
    start_time = max(current_time - 2.5, 0)
    end_time = current_time + 2.5
    relevant_data = data[(data["time"] >= start_time) & (data["time"] <= end_time)]

    screen.fill((255, 255, 255))
    for _, row in relevant_data.iterrows():
        x = (row["time"] - current_time + 2.5) * scale_x
        y = height - (row["frequency"] - min_frequency) * scale_y
        pygame.draw.circle(screen, row["color"], (int(x), int(y)), 3)

    pygame.draw.line(screen, (255, 0, 0), (width // 2, 0), (width // 2, height), 2)

    # Calculate and render FPS
    fps = clock.get_fps()
    fps_text = font.render(f"{fps:.2f} FPS", True, (0, 0, 0))
    screen.blit(fps_text, (10, 10))

    pygame.display.flip()
    clock.tick(20)

pygame.quit()
