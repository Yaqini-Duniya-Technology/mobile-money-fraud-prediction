import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "reports" / "xgb_ablation"

FILES = [
    "model.joblib",
    "model_contract.json",
]

def sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def main():
    artifacts = {}

    for filename in FILES:
        path = MODEL_DIR / filename

        if not path.is_file():
            raise FileNotFoundError(path)

        artifacts[filename] = {
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }

    report = {
        "model_version": "xgb_ablation_v1",
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "algorithm": "SHA-256",
        "artifacts": artifacts,
    }

    output = MODEL_DIR / "integrity.json"

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Artifact integrity manifest generated.")

    for name, details in artifacts.items():
        print(name)
        print(" SHA-256:", details["sha256"])
        print(" Size:", details["size_bytes"], "bytes")

    print("Saved:", output)


if __name__ == "__main__":
    main()
