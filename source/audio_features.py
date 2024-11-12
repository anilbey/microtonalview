"""Calculation of audio specific features."""

from pathlib import Path
import librosa
import numpy as np
import polars as pl
import torch
import torchcrepe


def calculate_loudness(wav_file: Path) -> np.ndarray:
    """Calculate the loudness of each frame in the audio."""
    y, sr = librosa.load(wav_file)
    frame_length = hop_length = int(0.01 * sr)  # 0.01 seconds for frame and hop length
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)
    return rms[0]


def extract_pitch_data_frame(wav_file: Path) -> pl.DataFrame:
    """Extract pitch data using torchcrepe and return a polars DataFrame."""
    audio, sr = torchcrepe.load.audio(str(wav_file))

    # Convert to mono if necessary
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)

    # Set device and batch size based on available GPU memory
    if torch.cuda.is_available():
        device = "cuda"
        torch.cuda.empty_cache()
        # Get total and available GPU memory
        total_memory = torch.cuda.get_device_properties(device).total_memory
        reserved_memory = torch.cuda.memory_reserved(device)
        allocated_memory = torch.cuda.memory_allocated(device)
        free_memory = total_memory - (reserved_memory + allocated_memory)
        free_memory_mb = free_memory / (1024 ** 2)

        # Estimate memory usage per batch element (this is an approximate value)
        memory_per_batch_element_mb = 2  # Adjust based on empirical tests

        # Introduce a safety margin (e.g., only use 80% of free memory)
        safety_margin = 0.8
        adjusted_free_memory_mb = free_memory_mb * safety_margin

        # Set batch_size based on available memory with safety margin
        batch_size = int(adjusted_free_memory_mb // memory_per_batch_element_mb)

        # Set conservative maximum limit for batch size
        batch_size = max(16, min(batch_size, 512))  # Maximum of 512 to avoid memory issues
    else:
        device = "cpu"
        batch_size = 128


    print(f"Using batch_size: {batch_size}")
    audio = audio.to(device)

    # Compute hop length for 10 ms steps
    hop_length = int(sr * 0.01)

    fmin, fmax = 50.0, 1200.0
    model = 'full'

    chunk_duration = 10  # seconds
    chunk_size = int(sr * chunk_duration)

    total_samples = audio.shape[-1]
    total_chunks = (total_samples + chunk_size - 1) // chunk_size

    chunks = []

    # Process audio in chunks
    for i, start in enumerate(range(0, total_samples, chunk_size), start=1):
        end = min(start + chunk_size, total_samples)
        audio_chunk = audio[:, start:end]

        print(f"Processing chunk {i} / {total_chunks}...")

        # Compute pitch and periodicity for the chunk
        pitch, periodicity = torchcrepe.predict(
            audio_chunk,
            sr,
            hop_length,
            fmin,
            fmax,
            model,
            batch_size=batch_size,
            device=device,
            return_periodicity=True
        )

        # Compute time vector for the chunk
        num_frames = pitch.shape[-1]
        time = (np.arange(num_frames) * hop_length / sr) + (start / sr)

        # Convert tensors to numpy arrays
        frequency = pitch.squeeze().cpu().numpy()
        confidence = periodicity.squeeze().cpu().numpy()

        # Create DataFrame for the chunk
        chunk_df = pl.DataFrame({
            "time": time,
            "frequency": frequency,
            "confidence": confidence
        })

        chunks.append(chunk_df)

    # Concatenate all chunks
    df = pl.concat(chunks)

    return df
