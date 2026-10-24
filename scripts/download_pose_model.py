"""Download the versioned official MediaPipe Lite model over verified HTTPS."""
from pathlib import Path
from urllib.request import urlopen
import hashlib
import zipfile

URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
DEST = Path(__file__).resolve().parents[1] / "models/pose_landmarker_lite.task"
SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    temporary = DEST.with_suffix(".download")
    try:
        with urlopen(URL, timeout=60) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != SHA256:
            raise ValueError("Model checksum mismatch; refusing to install")
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None or len(archive.namelist()) < 2:
                raise ValueError("Downloaded model is not a valid Tasks bundle")
        temporary.replace(DEST)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Model: {DEST}\nSource: {URL}\nSHA256: {hashlib.sha256(DEST.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
