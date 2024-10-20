"""Playing the audio files."""

import time
import simpleaudio

class AudioPlayer:
    def __init__(self, audio_segment):
        self.audio_segment = audio_segment
        self.play_obj = None
        self.start_time = None  # System time when playback started
        self.current_time = 0   # Current playback position in seconds
        self.is_playing_flag = False

    def play(self, start_time=0):
        self.stop()  # Stop any existing playback
        self.current_time = start_time
        self.start_time = time.time() - start_time
        self.is_playing_flag = True

        # Slice the audio segment from the start_time
        segment_to_play = self.audio_segment[start_time * 1000:]

        # Extract raw data
        raw_data = segment_to_play.raw_data

        # Get audio parameters
        num_channels = segment_to_play.channels
        bytes_per_sample = segment_to_play.sample_width
        sample_rate = segment_to_play.frame_rate

        # Play the raw data using simpleaudio
        self.play_obj = simpleaudio.play_buffer(
            raw_data,
            num_channels,
            bytes_per_sample,
            sample_rate
        )

    def stop(self):
        if self.play_obj is not None:
            self.play_obj.stop()
            self.play_obj = None
        self.is_playing_flag = False
        self.start_time = None

    def pause(self):
        if self.play_obj is not None:
            self.current_time = self.get_elapsed_time()
            self.play_obj.stop()
            self.play_obj = None
            self.is_playing_flag = False
            self.start_time = None

    def seek(self, time_sec):
        """Seek to a specific time in seconds without starting playback."""
        self.current_time = time_sec
        if self.is_playing_flag:
            self.play(start_time=time_sec)

    def get_elapsed_time(self):
        if self.is_playing_flag and self.start_time is not None:
            return time.time() - self.start_time
        else:
            return self.current_time

    def is_playing(self):
        if self.play_obj is not None:
            return self.play_obj.is_playing()
        return False
