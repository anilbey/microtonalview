"""Manages the switching of scenes."""

import signal
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import polars as pl
import pygame
import pygame_gui
from pydub import AudioSegment

from audio_features import extract_pitch_data_frame
from caching import hash_file, load_from_cache, save_to_cache
from controller.event_handler import handle_header_events, handle_visualiser_events
from controller.program_state import ProgramState
from dataframe_operations import (
    process_pitch_data,
    compute_x_positions_lazy,
    compute_y_positions_lazy,
    filter_data_by_time_window_lazy,
)
from model import Pitch
from view.player import PlayerView
from view.loading_screen import loading_screen
from controller.audio_player import AudioPlayer
from video_recorder import VideoRecorder


class HeaderWidgets:
    width: float
    ui_manager: pygame_gui.UIManager
    close_button: pygame_gui.elements.UIButton
    minimize_button: pygame_gui.elements.UIButton

    def __init__(self, width: float, ui_manager: pygame_gui.UIManager):
        """Initialize close and minimize buttons."""
        self.width = width
        self.ui_manager = ui_manager
        self.close_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((int(width) - 45, 10), (35, 35)),
            text="X",
            manager=ui_manager,
            object_id="#close_button",
        )
        self.minimize_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((int(width) - 85, 10), (35, 35)),
            text="-",
            manager=ui_manager,
            object_id="#minimize_button",
        )


class SceneManager:
    screen: pygame.Surface
    width: float
    height: float
    ui_manager: pygame_gui.UIManager
    header_widgets: HeaderWidgets

    def __init__(
        self,
        screen: pygame.Surface,
        width: float,
        height: float,
        ui_manager: pygame_gui.UIManager,
    ):
        """Initialize the scene manager and load header widgets."""
        self.screen = screen
        self.width = width
        self.height = height
        self.ui_manager = ui_manager
        self.header_widgets = HeaderWidgets(width, ui_manager)

    def display_menu(self) -> str | None:
        """Display the main menu and return the selected audio file path."""
        logo_image = pygame.image.load(Path("assets") / "microtonal-view.png")
        logo_rect = logo_image.get_rect(center=(self.width/2, self.height/3))

        load_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.width/2 - 150, self.height/2), (300, 80)),
            text="Load a WAV file",
            manager=self.ui_manager,
        )

        file_dialog: pygame_gui.windows.UIFileDialog | None = None
        selected_file: str | None = None
        program_running = True
        clock = pygame.time.Clock()

        while program_running:
            time_delta = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.ui_manager.process_events(event)
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.header_widgets.close_button:
                        pygame.quit()
                    elif event.ui_element == self.header_widgets.minimize_button:
                        pygame.display.iconify()
                    elif event.ui_element == load_button:
                        file_dialog = pygame_gui.windows.UIFileDialog(
                            rect=pygame.Rect(0, 0, 800, 600),
                            manager=self.ui_manager,
                            window_title="Open Audio File",
                            initial_file_path=str(Path.home()),
                            allow_picking_directories=False,
                            allowed_suffixes={".wav"}
                        )
                if event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                    if event.ui_element == file_dialog:
                        selected_file = event.text
                        program_running = False

            self.ui_manager.update(time_delta)
            self.screen.fill((255, 255, 255))
            self.screen.blit(logo_image, logo_rect)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

        load_button.kill()
        if file_dialog:
            file_dialog.kill()

        return selected_file

    def display_loading_screen(self, audio_file: str) -> Pitch:
        """Display the loading screen and process the pitch data."""
        with loading_screen(
            self.screen, int(self.width), int(self.height), Path("assets") / "microtonal-view.png"
        ) as loader:
            audio_hash: str = hash_file(audio_file)
            cached_data: pl.DataFrame | None = load_from_cache(audio_hash)

            with ThreadPoolExecutor(max_workers=2) as executor:
                if cached_data is not None:
                    raw_pitch_data = cached_data
                    print("Using cached data...")
                else:
                    future = executor.submit(extract_pitch_data_frame, audio_file)
                    print("Extracting pitch data...")

                    # Frame loop: extract pitch data
                    while not future.done():
                        handle_header_events(
                            self.ui_manager,
                            self.header_widgets.close_button,
                            self.header_widgets.minimize_button,
                        )
                        loader.render_loading_screen()
                        loader.update_stdout_display()
                        self.ui_manager.update(0.01)
                        self.ui_manager.draw_ui(self.screen)
                        pygame.display.flip()
                        pygame.time.Clock().tick(20)

                    raw_pitch_data = future.result()
                    save_to_cache(audio_hash, raw_pitch_data)

                print("Processing pitch data...")
                future_process = executor.submit(
                    process_pitch_data, raw_pitch_data, audio_file
                )

                # Frame loop: process pitch data
                while not future_process.done():
                    handle_header_events(
                        self.ui_manager,
                        self.header_widgets.close_button,
                        self.header_widgets.minimize_button,
                    )
                    loader.render_loading_screen()
                    loader.update_stdout_display()
                    self.ui_manager.update(0.01)
                    self.ui_manager.draw_ui(self.screen)
                    pygame.display.flip()
                    pygame.time.Clock().tick(20)

                pitch = future_process.result()

        return pitch

    def display_player(
        self, 
        pitch: Pitch, 
        audio_file: str, 
        background_image_path: str | None = None,
        record_to_file: str | None = None,
        fps: int = 60
    ) -> ProgramState:
        """Display the player scene and handle the main loop.
        
        Two modes:
        1. Play mode (record_to_file=None): Interactive playback with display
        2. Record mode (record_to_file set): Headless video generation, no display
        
        Args:
            pitch: Pitch data to visualize
            audio_file: Path to audio file
            background_image_path: Optional background image
            record_to_file: Optional output video file path for recording (always headless)
            fps: Frames per second for recording (default: 60)
        """
        # Initialize audio player
        audio_segment = AudioSegment.from_wav(audio_file)
        player = AudioPlayer(audio_segment)
        
        # Only play audio through speakers if NOT recording
        # When recording, ffmpeg will add the audio directly from the file
        if not record_to_file:
            player.play()  # Start playback

        # Get music length in seconds
        music_length = len(audio_segment) / 1000.0

        player_view = PlayerView(
            self.screen,
            self.width,
            self.height,
            self.ui_manager,
            pitch,
            music_length,
            background_image_path=background_image_path,
        )

        program_state = ProgramState.PLAYING
        clock = pygame.time.Clock()

        lazy_pitch_data = pitch.annotated_pitch_data_frame.lazy()
        
        # Initialize video recorder if recording mode is enabled
        recorder = None
        frame_count = 0  # Track frame number for recording
        interrupted = False  # Track Ctrl+C
        
        def signal_handler(signum, frame):
            nonlocal interrupted
            print("\n\n⚠️  Interrupted! Finalizing video...")
            interrupted = True
        
        if record_to_file:
            # Set up signal handler for Ctrl+C (optional early stop)
            signal.signal(signal.SIGINT, signal_handler)
            
            recorder = VideoRecorder(
                record_to_file, 
                self.width, 
                self.height, 
                fps=fps,
                audio_file=audio_file
            )
            recorder.start()
            # Set target FPS for recording
            target_fps = fps
            print("\n🎬 RECORDING MODE (Headless)")
            print(f"   Target FPS: {fps}")
            print(f"   Audio length: {music_length:.2f} seconds")
            print(f"   Expected frames: {int(music_length * fps)}")
            print("   Video will automatically end when audio finishes")
            print("   Starting frame generation...\n")
        else:
            # Normal interactive mode - use 25 FPS
            target_fps = 25

        # Main loop
        while program_state != ProgramState.TERMINATED and not interrupted:
            # In recording mode: don't limit FPS, generate frames as fast as possible
            # In playback mode: limit to target FPS for smooth real-time display
            if not recorder:
                time_delta = clock.tick(target_fps) / 1000.0
            else:
                # Recording mode: no FPS limiting, use fixed time delta for UI updates
                time_delta = 1.0 / fps
                # Just process events without limiting speed
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        program_state = ProgramState.TERMINATED

            # Only handle interactive events in playback mode
            if not recorder:
                program_state = handle_visualiser_events(
                    self.ui_manager,
                    self.header_widgets.close_button,
                    self.header_widgets.minimize_button,
                    player,
                    player_view.slider,
                    music_length,
                    player_view.play_pause_button,
                    program_state,
                )

            # In recording mode, use frame-based timing for perfect sync
            # In playback mode, use real-time audio position
            if recorder:
                current_time = frame_count / fps
            else:
                current_time = player.get_elapsed_time()
            
            # In recording mode, automatically quit when we reach the end of audio
            if recorder and current_time >= music_length:
                program_state = ProgramState.TERMINATED
                break

            player_view.update_controls(current_time, program_state)

            # Update visuals based on current_time
            dataframe_window_to_display_lazy = filter_data_by_time_window_lazy(
                lazy_pitch_data, current_time
            ).with_columns(
                [
                    compute_x_positions_lazy(current_time, player_view.scale_x).alias("x"),
                    compute_y_positions_lazy(
                        player_view.usable_height,
                        player_view.padding_bottom,
                        pitch.min_frequency,
                        player_view.scale_y,
                    ).alias("y"),
                ]
            )
            dataframe_window_to_display = dataframe_window_to_display_lazy.collect()

            # Handle playback - only in interactive mode, not during recording
            if not recorder:
                if program_state == ProgramState.PLAYING:
                    if not player.is_playing():
                        player.play(start_time=current_time)
                elif program_state == ProgramState.PAUSED:
                    if player.is_playing():
                        player.pause()

            player_view.update_dynamic_elements(dataframe_window_to_display, current_time)
            player_view.render()
            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.screen)

            # Update display only in play mode (not during recording)
            if not recorder:
                pygame.display.flip()
            else:
                # Recording mode: write frame to video
                recorder.write_frame(self.screen)
                frame_count += 1
                
                # Print progress every 60 frames (roughly every second of video at 60fps)
                if frame_count % 60 == 0:
                    progress = (current_time / music_length) * 100
                    print(f"   Frame {frame_count:5d} | Time: {current_time:6.2f}s / {music_length:.2f}s | {progress:5.1f}%")
        
        # Finalize recording if it was enabled
        if recorder:
            print("\n✅ Recording complete!")
            print(f"   Total frames written: {frame_count}")
            print(f"   Expected frames: {int(music_length * fps)}")
            print(f"   Video duration: {frame_count / fps:.2f} seconds")
            recorder.finish()

        return program_state
