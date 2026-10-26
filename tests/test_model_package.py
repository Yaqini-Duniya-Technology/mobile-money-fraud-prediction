
"""Security and integrity tests for FraudGuard model packages."""

import hashlib
import json
import tempfile
import unittest
import zipfile

from pathlib import Path

from training.install_model import install


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestModelPackage(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.package = self.root / "model.zip"
        self.destination = self.root / "installed"

        # Dummy bytes: never deserialize these test artifacts.
        self.model_bytes = b"fraudguard-test-model"

        self.contract = {
            "schema_version": 1,
            "model_version": "xgb_ablation_v1",
            "model_file": "model.joblib",
            "score_calibrated": False,
            "feature_names": [
                "step",
                "type",
                "amount",
                "oldbalanceOrg",
                "oldbalanceDest",
            ],
        }

    def build_package(
        self,
        *,
        corrupt_model=False,
        extra_file=False,
        traversal=False,
        invalid_contract=False,
    ):
        contract = dict(self.contract)

        if invalid_contract:
            contract["model_version"] = "unknown_model"

        contract_bytes = json.dumps(
            contract
        ).encode("utf-8")

        manifest = {
            "artifacts": {
                "model.joblib": {
                    "sha256": sha256_bytes(self.model_bytes),
                    "size_bytes": len(self.model_bytes),
                },
                "model_contract.json": {
                    "sha256": sha256_bytes(contract_bytes),
                    "size_bytes": len(contract_bytes),
                },
            }
        }

        model_content = (
            b"tampered-model"
            if corrupt_model
            else self.model_bytes
        )

        with zipfile.ZipFile(
            self.package,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "model.joblib",
                model_content,
            )
            archive.writestr(
                "model_contract.json",
                contract_bytes,
            )
            archive.writestr(
                "integrity.json",
                json.dumps(manifest),
            )

            if extra_file:
                archive.writestr(
                    "unexpected.txt",
                    "unexpected content",
                )

            if traversal:
                archive.writestr(
                    "../outside.txt",
                    "unsafe path",
                )

        return sha256_file(self.package)

    def test_valid_package_installs(self):
        expected_hash = self.build_package()

        install(
            self.package,
            self.destination,
            expected_hash,
        )

        self.assertTrue(
            (self.destination / "model.joblib").is_file()
        )
        self.assertTrue(
            (self.destination / "model_contract.json").is_file()
        )
        self.assertTrue(
            (self.destination / "integrity.json").is_file()
        )

    def test_wrong_package_hash_rejected(self):
        self.build_package()

        with self.assertRaises(ValueError):
            install(
                self.package,
                self.destination,
                "0" * 64,
            )

        self.assertFalse(self.destination.exists())

    def test_tampered_model_rejected(self):
        # ZIP checksum matches the tampered ZIP, but
        # its internal model hash does not match.
        expected_hash = self.build_package(
            corrupt_model=True
        )

        with self.assertRaises(ValueError):
            install(
                self.package,
                self.destination,
                expected_hash,
            )

        self.assertFalse(self.destination.exists())

    def test_unexpected_file_rejected(self):
        expected_hash = self.build_package(
            extra_file=True
        )

        with self.assertRaises(ValueError):
            install(
                self.package,
                self.destination,
                expected_hash,
            )

        self.assertFalse(self.destination.exists())

    def test_path_traversal_rejected(self):
        expected_hash = self.build_package(
            traversal=True
        )

        with self.assertRaises(ValueError):
            install(
                self.package,
                self.destination,
                expected_hash,
            )

        self.assertFalse(self.destination.exists())
        self.assertFalse(
            (self.root / "outside.txt").exists()
        )

    def test_existing_installation_not_overwritten(self):
        expected_hash = self.build_package()

        self.destination.mkdir()
        marker = self.destination / "existing.txt"
        marker.write_text("keep this file")

        with self.assertRaises(FileExistsError):
            install(
                self.package,
                self.destination,
                expected_hash,
            )

        self.assertEqual(
            marker.read_text(),
            "keep this file",
        )

    def test_invalid_model_version_rejected(self):
        expected_hash = self.build_package(
            invalid_contract=True
        )

        with self.assertRaises(ValueError):
            install(
                self.package,
                self.destination,
                expected_hash,
            )

        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
