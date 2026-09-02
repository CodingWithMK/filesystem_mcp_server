import asyncio
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


SRC = Path(__file__).parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import boundaryattest
import main


def make_keys(tmp_path: Path) -> tuple[Path, bytes]:
    private_key = Ed25519PrivateKey.generate()
    private_path = tmp_path / "private.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_path, public_pem


@pytest.fixture
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main, "ALLOWED_PATHS", [tmp_path])
    monkeypatch.setattr(main, "ALLOWED_EXTENSIONS", {"txt"})
    monkeypatch.setattr(
        main,
        "BOUNDARY_ATTESTOR",
        boundaryattest.BoundaryAttestor(boundaryattest.BoundaryAttestConfig(False)),
    )
    return main


def enable(server, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, bytes]:
    private_path, public_pem = make_keys(tmp_path)
    receipt_dir = tmp_path / "receipts"
    monkeypatch.setattr(
        server,
        "BOUNDARY_ATTESTOR",
        boundaryattest.BoundaryAttestor(
            boundaryattest.BoundaryAttestConfig(True, private_path, receipt_dir)
        ),
    )
    return receipt_dir, public_pem


def only_receipt(receipt_dir: Path) -> tuple[Path, dict]:
    paths = list(receipt_dir.glob("*.json"))
    assert len(paths) == 1
    return paths[0], json.loads(paths[0].read_text(encoding="utf-8"))


def test_disabled_preserves_write_and_creates_no_receipt(server, tmp_path):
    target = tmp_path / "disabled.txt"
    result = asyncio.run(server.write_file(str(target), "hello"))
    assert target.read_bytes() == b"hello"
    assert result == f"Successfully committed content to {target}"

    destination = tmp_path / "disabled-move"
    destination.mkdir()
    move_result = asyncio.run(server.move_file(str(target), str(destination)))
    moved = destination / target.name
    assert moved.read_bytes() == b"hello"
    assert move_result == f"Successfully moved '{target}' to '{destination}' coordinates."

    monkeypatch_trash = lambda path: Path(path).unlink()
    original_trash = server.send2trash
    server.send2trash = monkeypatch_trash
    try:
        delete_result = asyncio.run(server.delete_file(str(moved)))
    finally:
        server.send2trash = original_trash
    assert not moved.exists()
    assert delete_result == (
        f"Successfully dispatched file {moved} to environment recycling bin."
    )
    assert not (tmp_path / "receipts").exists()


def test_write_receipt_exact_bytes_and_tamper(server, tmp_path, monkeypatch):
    receipt_dir, public_pem = enable(server, tmp_path, monkeypatch)
    target = tmp_path / "written.txt"
    target.write_bytes(b"before\n")
    asyncio.run(server.write_file(str(target), "after\r\n"))
    receipt_path, receipt = only_receipt(receipt_dir)
    assert receipt["claim"]["pre_operation_hash"] == boundaryattest.sha256_bytes(b"before\n")
    assert receipt["claim"]["artifact_hash"] == boundaryattest.sha256_bytes(b"before\nafter\r\n")
    assert receipt["claim"]["input_hash"] == boundaryattest.sha256_bytes(b"after\r\n")
    assert boundaryattest.verify_receipt(receipt_path.read_text(), public_pem, target) == {
        "ok": True,
        "artifact_ok": True,
        "expected_artifact_hash": receipt["claim"]["artifact_hash"],
        "actual_artifact_hash": receipt["claim"]["artifact_hash"],
    }
    target.write_bytes(target.read_bytes() + b"tamper")
    assert boundaryattest.verify_receipt(
        receipt_path.read_text(), public_pem, target
    )["artifact_ok"] is False


def test_move_binds_materialized_directory_destination(server, tmp_path, monkeypatch):
    receipt_dir, public_pem = enable(server, tmp_path, monkeypatch)
    source = tmp_path / "source.txt"
    destination_dir = tmp_path / "destination"
    destination_dir.mkdir()
    source.write_bytes(b"move bytes")
    asyncio.run(server.move_file(str(source), str(destination_dir)))
    final_destination = destination_dir / source.name
    receipt_path, receipt = only_receipt(receipt_dir)
    assert receipt["claim"]["target_ref"] == "allowed_root_0:destination/source.txt"
    assert receipt["claim"]["artifact_hash"] == boundaryattest.sha256_bytes(b"move bytes")
    assert boundaryattest.verify_receipt(receipt_path.read_text(), public_pem, final_destination)["ok"]
    directory_argument_digest = boundaryattest.materialized_action_hash({
        "action_type": "mcp.filesystem.move_file",
        "resolved_source": str(source),
        "resolved_final_destination": str(destination_dir),
        "operation_semantics": "move",
    })
    assert receipt["claim"]["materialized_action_hash"] != directory_argument_digest


def test_delete_binds_pre_delete_bytes_without_real_trash(server, tmp_path, monkeypatch):
    receipt_dir, public_pem = enable(server, tmp_path, monkeypatch)
    target = tmp_path / "deleted.txt"
    target.write_bytes(b"delete me\x00")

    def fake_trash(path: str):
        Path(path).unlink()

    monkeypatch.setattr(server, "send2trash", fake_trash)
    asyncio.run(server.delete_file(str(target)))
    receipt_path, receipt = only_receipt(receipt_dir)
    expected = boundaryattest.sha256_bytes(b"delete me\x00")
    assert not target.exists()
    assert receipt["claim"]["artifact_hash"] == expected
    assert receipt["claim"]["deleted_artifact_hash"] == expected
    assert receipt["claim"]["output_hash"] is None
    assert boundaryattest.verify_receipt(receipt_path.read_text(), public_pem)["ok"]


def test_signed_claim_tampering_fails(server, tmp_path, monkeypatch):
    receipt_dir, public_pem = enable(server, tmp_path, monkeypatch)
    asyncio.run(server.write_file(str(tmp_path / "tamper.txt"), "original"))
    receipt_path, receipt = only_receipt(receipt_dir)
    receipt["claim"]["status"] = "changed"
    assert boundaryattest.verify_receipt(json.dumps(receipt), public_pem) == {
        "ok": False,
        "reason": "invalid_signature",
    }


def test_receipt_failure_reports_successful_side_effect(server, tmp_path, monkeypatch):
    target = tmp_path / "survives.txt"
    private_path, _ = make_keys(tmp_path)
    invalid_receipt_dir = tmp_path / "not-a-directory"
    invalid_receipt_dir.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(
        server,
        "BOUNDARY_ATTESTOR",
        boundaryattest.BoundaryAttestor(
            boundaryattest.BoundaryAttestConfig(
                True, private_path, invalid_receipt_dir
            )
        ),
    )
    result = asyncio.run(server.write_file(str(target), "committed"))
    assert target.read_bytes() == b"committed"
    assert "Successfully committed" in result
    assert "attestation failed after the filesystem action succeeded" in result
