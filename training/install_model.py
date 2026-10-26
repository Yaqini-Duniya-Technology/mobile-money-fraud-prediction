
"""Verify and install a trusted FraudGuard model package."""

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile

from pathlib import Path


REQUIRED_FILES = {
    "model.joblib",
    "model_contract.json",
    "integrity.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def install(package: Path, destination: Path, expected_hash: str):
    package = package.resolve()
    destination = destination.resolve()

    if not package.is_file():
        raise FileNotFoundError(package)

    if (
        len(expected_hash) != 64
        or any(c not in "0123456789abcdef"
               for c in expected_hash.lower())
    ):
        raise ValueError("Expected SHA-256 must be 64 hex characters")

    actual_hash = sha256(package)

    if actual_hash.lower() != expected_hash.lower():
        raise ValueError("Package SHA-256 mismatch")

    if destination.exists():
        raise FileExistsError(
            f"Destination already exists: {destination}"
        )

    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)

        with zipfile.ZipFile(package) as archive:
            names = archive.namelist()

            if (
                len(names) != len(REQUIRED_FILES)
                or set(names) != REQUIRED_FILES
            ):
                raise ValueError("Unexpected archive contents")

            for item in archive.infolist():
                if item.is_dir():
                    raise ValueError("Archive contains directories")

                if item.file_size > 20 * 1024 * 1024:
                    raise ValueError("Artifact exceeds size limit")

                with archive.open(item) as source:
                    with (staging / item.filename).open("wb") as target:
                        shutil.copyfileobj(source, target)

        manifest = json.loads(
            (staging / "integrity.json").read_text(
                encoding="utf-8"
            )
        )

        for filename in ("model.joblib", "model_contract.json"):
            expected = manifest["artifacts"][filename]
            file_path = staging / filename

            if sha256(file_path) != expected["sha256"]:
                raise ValueError(f"Artifact hash mismatch: {filename}")

            if file_path.stat().st_size != expected["size_bytes"]:
                raise ValueError(f"Artifact size mismatch: {filename}")

        contract = json.loads(
            (staging / "model_contract.json").read_text(
                encoding="utf-8"
            )
        )

        if contract.get("schema_version") != 1:
            raise ValueError("Unsupported contract version")

        if contract.get("model_file") != "model.joblib":
            raise ValueError("Unexpected model filename")

        if contract.get("model_version") != "xgb_ablation_v1":
            raise ValueError("Unexpected model version")

        if contract.get("score_calibrated") is not False:
            raise ValueError("Unexpected calibration status")

        destination.parent.mkdir(parents=True, exist_ok=True)

        # Copy only after all package checks succeed.
        shutil.copytree(staging, destination)

    print("Model package installed successfully.")
    print("Destination:", destination)
    print("Model version:", contract["model_version"])
    print("Package SHA-256:", actual_hash)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--sha256", required=True)

    args = parser.parse_args()

    install(
        package=args.package,
        destination=args.destination,
        expected_hash=args.sha256,
    )


if __name__ == "__main__":
    main()
