import argparse
import subprocess
import sys
import time


def record_script(script, args, output_filename):
    # Start the Python script
    script_process = subprocess.Popen([sys.executable, script] + args)
    time.sleep(1)

    # Updated ffmpeg command to use the specified audio source
    ffmpeg_command = [
        'ffmpeg',
        '-y',  # Overwrite existing files
        '-f', 'x11grab',
        '-video_size', f"{1920}x{1020}",  # Use actual window size
        '-i', f":0.0+{0},{0}",  # Use actual window position
        '-f', 'pulse', '-ac', '2', 
        '-i', 'alsa_output.usb-Focusrite_Scarlett_2i2_USB-00.analog-stereo.2.monitor',  # Specified audio source
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        output_filename
    ]

    recording_process = subprocess.Popen(ffmpeg_command)

    # Wait for the Python script to finish
    script_process.wait()

    # Stop the recording
    recording_process.terminate()
    recording_process.wait()


def main():
    parser = argparse.ArgumentParser(description="Record a Python script execution")
    parser.add_argument("script", help="Python script to record")
    parser.add_argument("output", help="Output MP4 filename")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the Python script")

    args = parser.parse_args()
    record_script(args.script, args.args, args.output)

if __name__ == "__main__":
    main()
