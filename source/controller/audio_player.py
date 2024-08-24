"""Playing the audio files."""

import time
from pydub.playback import _play_with_simpleaudio


class AudioPlayer:
    def __init__(self, audio_segment):
        self.audio_segment = audio_segment
        self.playback = None
        self.start_time = None
        self.pause_time = 0

    def play(self, start_time=0):
        self.stop()  # Stop any existing playback
        self.start_time = time.time() - start_time
        self.playback = _play_with_simpleaudio(self.audio_segment[start_time * 1000 :])
        self.pause_time = start_time  # Set pause time to start_time on play

    def stop(self):
        if self.playback is not None:
            self.playback.stop()
            self.playback = None

    def pause(self):
        if self.playback is not None:
            self.pause_time = self.get_elapsed_time()
            self.playback.stop()

    def resume(self):
        self.play(start_time=self.pause_time)

    def get_elapsed_time(self):
        if self.playback is None:
            return 0
        return time.time() - self.start_time

    def is_playing(self):
        return self.playback is not None and self.playback.is_playing()
