import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "xgb_ablation"
OUTPUT_DIR = ROOT / "model_packages"
OUTPUT = OUTPUT_DIR / "fraudguard-xgb-ablation-v1.zip"

FILES = (
    "model.joblib",
    "model_contract.json",
    "integrity.json",
)


def sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def main():
    manifest_path = SOURCE / "integrity.json"

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    # Verify against the recorded local manifest.
    for filename in FILES[:2]:
        path = SOURCE / filename

        if not path.is_file():
            raise FileNotFoundError(path)

        expected = manifest["artifacts"][filename]

        if sha256(path) != expected["sha256"]:
            raise RuntimeError(
                f"SHA-256 mismatch: {filename}"
            )

        if path.stat().st_size != expected["size_bytes"]:
            raise RuntimeError(
                f"File size mismatch: {filename}"
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        OUTPUT,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for filename in FILES:
            archive.write(
                SOURCE / filename,
                arcname=filename,
            )

    with zipfile.ZipFile(OUTPUT, "r") as archive:
        if set(archive.namelist()) != set(FILES):
            raise RuntimeError("Unexpected ZIP contents")

        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity test failed")

    print("Model package created:", OUTPUT)
    print("Package size:", OUTPUT.stat().st_size, "bytes")
    print("Package SHA-256:", sha256(OUTPUT))
    print("Included files:", ", ".join(FILES))
    print("Package verification passed.")


if __name__ == "__main__":
    main()
