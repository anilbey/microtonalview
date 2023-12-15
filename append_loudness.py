import librosa
import polars as pl


def calculate_loudness(y, frame_length, hop_length):
    """Calculate the loudness of each frame in the audio."""
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)
    return rms[0]


def append_loudness_to_csv(wav_file, csv_file, output_file):
    # Load the WAV file
    y, sr = librosa.load(wav_file)

    # Define the frame and hop length (0.01 seconds)
    frame_length = hop_length = int(0.01 * sr)

    # Calculate loudness
    loudness = calculate_loudness(y, frame_length, hop_length)

    # Read the existing CSV data
    df = pl.read_csv(csv_file)

    # Ensure loudness array is not longer than the dataframe
    loudness = loudness[: len(df)]
    # Append loudness data to the DataFrame
    df = df.with_columns(pl.Series("loudness", loudness))

    # Write the updated data back to a new CSV file
    df.write_csv(output_file)


# Example usage
append_loudness_to_csv(
    "tunar-hüzzam.wav", "tunar-hüzzam.f0.csv", "tunar-hüzzam-loudness.csv"
)
