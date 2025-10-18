"""Video recorder that pipes pygame frames and audio directly to ffmpeg."""
import subprocess
import numpy as np
import pygame


class VideoRecorder:
    """Records pygame display frames and audio to video file via ffmpeg pipe."""
    
    # FFmpeg encoding parameters (configurable class constants)
    VIDEO_CRF = 28              # H.264 quality (0-51, lower=better, 28=medium quality, good balance)
    VIDEO_PRESET = 'veryfast'   # Encoding speed preset (faster than default, good quality)
    AUDIO_BITRATE = '128k'      # Audio bitrate for AAC (sufficient for most music)
    PROGRESS_INTERVAL = 60      # Print progress every N frames (roughly 1 second at 60fps)
    
    def __init__(self, filename: str, width: int, height: int, fps: int = 60, audio_file: str | None = None):
        """
        Initialize the video recorder.
        
        Args:
            filename: Output video filename (must end with .mp4, .mkv, or .avi)
            width: Video width in pixels (must be > 0)
            height: Video height in pixels (must be > 0)
            fps: Frames per second (must be 1-120)
            audio_file: Optional path to audio file to include in video
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid dimensions: {width}x{height} (must be positive)")
        if fps <= 0 or fps > 120:
            raise ValueError(f"Invalid FPS: {fps} (must be 1-120)")
        if not filename:
            raise ValueError("Filename cannot be empty")
        if not filename.lower().endswith(('.mp4', '.mkv', '.avi')):
            raise ValueError(f"Unsupported video format: {filename} (use .mp4, .mkv, or .avi)")
        
        self.filename = filename
        self.width = width
        self.height = height
        self.fps = fps
        self.audio_file = audio_file
        self.process = None
        self.frame_count = 0  # Track frames written
        
    def start(self):
        """Start the ffmpeg process."""
        # Base command for video input from stdin
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-loglevel', 'error',  # Only show errors (prevents stderr buffer issues)
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'rgb24',
            '-framerate', str(self.fps),  # Input frame rate
            '-i', '-',  # Read video from stdin
        ]
        
        # Add audio input if provided
        if self.audio_file:
            command.extend([
                '-i', self.audio_file,
                '-c:a', 'aac',
                '-b:a', self.AUDIO_BITRATE,
            ])
        
        # Output settings
        command.extend([
            '-c:v', 'libx264',
            '-preset', self.VIDEO_PRESET,  # Fast encoding for real-time
            '-pix_fmt', 'yuv420p',
            '-crf', str(self.VIDEO_CRF),  # High quality
            '-r', str(self.fps),  # Output frame rate
            '-vsync', 'cfr',  # Constant frame rate - crucial for correct timing!
        ])
        
        # If audio is provided, ensure video and audio are synced
        if self.audio_file:
            command.extend([
                '-shortest',  # Stop when shortest stream ends
            ])
        
        command.append(self.filename)
        
        # Print the command for debugging
        print(f"\n{'='*60}")
        print(f"Recording started: {self.filename}")
        print(f"Resolution: {self.width}x{self.height} @ {self.fps} FPS")
        if self.audio_file:
            print(f"Audio: {self.audio_file}")
        print(f"FFmpeg command: {' '.join(command)}")
        print(f"{'='*60}\n")
        
        # Start ffmpeg process
        # CRITICAL: stderr must be DEVNULL or consumed in thread to prevent deadlock!
        # FFmpeg writes progress info to stderr, which can fill the pipe buffer
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL  # Prevent stderr buffer from filling and causing deadlock
        )
        
    def write_frame(self, surface: pygame.Surface):
        """
        Write a single frame from pygame surface to ffmpeg.
        
        Args:
            surface: Pygame surface to capture
            
        Raises:
            RuntimeError: If recorder not started or ffmpeg process terminated
        """
        if self.process is None:
            raise RuntimeError("Recorder not started. Call start() first.")
        
        # Check if ffmpeg process is still running
        if self.process.poll() is not None:
            raise RuntimeError(
                f"FFmpeg process terminated unexpectedly with code {self.process.returncode}. "
                f"Recorded {self.frame_count} frames before failure."
            )
        
        # Convert pygame surface to numpy array
        # pygame uses (width, height, 3) but we need (height, width, 3)
        frame = pygame.surfarray.array3d(surface)
        
        # Transpose from (width, height, channels) to (height, width, channels)
        frame = np.transpose(frame, (1, 0, 2))
        
        # Write frame to ffmpeg stdin
        try:
            self.process.stdin.write(frame.tobytes())
            self.frame_count += 1
            
            # Print progress at regular intervals
            if self.frame_count % self.PROGRESS_INTERVAL == 0:
                print(f"Recorded {self.frame_count} frames ({self.frame_count / self.fps:.1f}s)", end='\r')
        except BrokenPipeError:
            # Expected if audio ends early with -shortest flag
            pass
        except OSError as e:
            raise RuntimeError(f"Failed to write frame to ffmpeg: {e}") from e
    
    def finish(self):
        """Close the ffmpeg process and finalize the video."""
        if self.process:
            print(f"\nFinalizing video... (wrote {self.frame_count} frames total)")
            self.process.stdin.close()
            returncode = self.process.wait()
            
            # Check return code
            if returncode != 0:
                print(f"⚠️  FFmpeg finished with return code: {returncode}")
                print("   Video may be incomplete or corrupted")
            else:
                duration = self.frame_count / self.fps
                print("✓ Recording completed successfully!")
                print(f"  File: {self.filename}")
                print(f"  Frames: {self.frame_count}")
                print(f"  Duration: {duration:.2f}s @ {self.fps} FPS")
            
            self.process = None
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.finish()
    
    def __del__(self):
        """Ensure process is cleaned up if object is garbage collected."""
        if self.process and self.process.poll() is None:
            # Process still running, force cleanup
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                # If terminate fails, kill it
                try:
                    self.process.kill()
                except Exception:
                    pass  # Best effort cleanup
