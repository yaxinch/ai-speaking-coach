import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from app.providers.errors import ProviderError


def normalize_to_pcm_wav(source: Path, *, ffmpeg_exe: str | None = None) -> Path:
    """Create a temporary Azure/Gemini-compatible 16 kHz mono PCM WAV."""
    output = source.with_name(f".{source.stem}.speech.wav")
    command = [
        ffmpeg_exe or get_ffmpeg_exe(),
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        output.unlink(missing_ok=True)
        raise ProviderError("The uploaded audio could not be prepared for speech analysis.") from exc
    if completed.returncode != 0 or not output.exists() or output.stat().st_size == 0:
        output.unlink(missing_ok=True)
        raise ProviderError("The uploaded audio could not be decoded. Please record your answer again.", status_code=400)
    return output
