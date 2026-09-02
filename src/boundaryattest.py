"""Small optional BoundaryAttest Interop Profile v0.1 adapter.

The filesystem server remains the authority for validation and execution.  This
module only signs and persists evidence after selected operations succeed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REQUIRED_CLAIM_FIELDS = (
    "receipt_version",
    "receipt_role",
    "event_id",
    "timestamp",
    "action_type",
    "status",
)
TOP_LEVEL_FIELDS = ("claim", "signature", "public_key_id")
TRUE_VALUES = {"1", "true", "yes", "on"}
KEY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_SAFE_INTEGER = 2**53 - 1


def _check_canonical_subset(value: Any, path: str = "claim") -> None:
    """Apply the same portable subset used by BoundaryAttest's Python adapter."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not KEY_NAME.fullmatch(key):
                raise ValueError(f"{path}: keys must be lowercase ASCII snake_case: {key!r}")
            _check_canonical_subset(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_canonical_subset(child, f"{path}[{index}]")
    elif isinstance(value, bool) or value is None or isinstance(value, str):
        return
    elif isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ValueError(f"{path}: integer is outside JavaScript's safe integer range")
    elif isinstance(value, float):
        raise ValueError(f"{path}: floating-point values are not supported")
    else:
        raise ValueError(f"{path}: unsupported JSON value")


def canonical_json_bytes(value: Any) -> bytes:
    """Match BoundaryAttest v0.1 stableJson for this ASCII-keyed adapter."""
    _check_canonical_subset(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def materialized_action_hash(action: Mapping[str, Any]) -> str:
    """Hash a deterministic private representation of the executed action."""
    return sha256_bytes(canonical_json_bytes(action))


def logical_target_ref(path: Path, allowed_paths: Sequence[Path]) -> str:
    """Represent an already-validated path without disclosing its absolute root."""
    for index, root in enumerate(allowed_paths):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        suffix = relative.as_posix()
        return f"allowed_root_{index}:{suffix if suffix != '.' else '.'}"
    raise ValueError("resolved path does not match a configured allowed root")


@dataclass(frozen=True)
class BoundaryAttestConfig:
    enabled: bool
    private_key: Path | None = None
    receipt_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "BoundaryAttestConfig":
        raw_enabled = os.environ.get("BOUNDARYATTEST_ENABLED", "false")
        enabled = raw_enabled.strip().lower() in TRUE_VALUES
        key = os.environ.get("BOUNDARYATTEST_PRIVATE_KEY")
        receipt_dir = os.environ.get("BOUNDARYATTEST_RECEIPT_DIR")
        return cls(
            enabled=enabled,
            private_key=Path(key).expanduser() if key else None,
            receipt_dir=Path(receipt_dir).expanduser() if receipt_dir else None,
        )


class BoundaryAttestor:
    def __init__(self, config: BoundaryAttestConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "BoundaryAttestor":
        return cls(BoundaryAttestConfig.from_env())

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def emit(self, claim: dict[str, Any]) -> Path | None:
        """Sign and atomically publish one receipt; return None when disabled."""
        if not self.enabled:
            return None
        if self.config.private_key is None:
            raise ValueError("BOUNDARYATTEST_PRIVATE_KEY is required when enabled")
        if self.config.receipt_dir is None:
            raise ValueError("BOUNDARYATTEST_RECEIPT_DIR is required when enabled")

        # Lazy import keeps the default installation dependency-free.
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError as exc:
            raise RuntimeError(
                "BoundaryAttest requires the optional 'boundaryattest' dependency extra"
            ) from exc

        private_key = serialization.load_pem_private_key(
            self.config.private_key.read_bytes(), password=None
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("BoundaryAttest private key must be Ed25519 PKCS #8 PEM")

        public_der = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        receipt = {
            "claim": claim,
            "signature": base64.b64encode(
                private_key.sign(canonical_json_bytes(claim))
            ).decode("ascii"),
            "public_key_id": sha256_bytes(public_der),
        }
        rendered = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        receipt_dir = self.config.receipt_dir
        receipt_dir.mkdir(parents=True, exist_ok=True)
        destination = receipt_dir / f"{claim['event_id']}.json"
        temporary = receipt_dir / f".{claim['event_id']}.{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            # Hard-link publication is atomic and fails rather than overwriting.
            os.link(temporary, destination)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return destination


def new_claim(action_type: str, target_ref: str, **fields: Any) -> dict[str, Any]:
    return {
        "receipt_version": "0.1",
        "receipt_role": "server_attested",
        "event_id": "evt_" + uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        ),
        "action_type": action_type,
        "status": "success",
        "target_ref": target_ref,
        **fields,
    }


def append_attestation_result(
    success: str,
    attestor: BoundaryAttestor,
    claim_factory: Callable[[], dict[str, Any]],
) -> str:
    """Build and emit evidence without disguising a completed side effect."""
    if not attestor.enabled:
        return success
    try:
        claim = claim_factory()
        receipt_path = attestor.emit(claim)
        return f"{success} BoundaryAttest receipt: {receipt_path}"
    except Exception as exc:
        warning = f"BoundaryAttest attestation failed after the filesystem action succeeded: {exc}"
        print(warning, file=sys.stderr)
        return f"{success} WARNING: {warning}"


def verify_receipt(
    receipt_text: str,
    public_key_pem: bytes,
    artifact: Path | None = None,
) -> dict[str, Any]:
    """Verify v0.1 structure/signature and optionally the signed artifact hash."""
    def fail(reason: str) -> dict[str, Any]:
        return {"ok": False, "reason": reason}

    try:
        receipt = json.loads(receipt_text)
    except (json.JSONDecodeError, ValueError):
        return fail("invalid_json")
    if not isinstance(receipt, dict):
        return fail("invalid_receipt")
    for field in TOP_LEVEL_FIELDS:
        if field not in receipt:
            return fail(f"missing_top_level_field:{field}")
    for field in receipt:
        if field not in TOP_LEVEL_FIELDS:
            return fail(f"unexpected_top_level_field:{field}")
    claim = receipt["claim"]
    if not isinstance(claim, dict):
        return fail("claim_not_object")
    if not isinstance(receipt["signature"], str) or not isinstance(receipt["public_key_id"], str):
        return fail("invalid_receipt")
    for field in REQUIRED_CLAIM_FIELDS:
        if field not in claim:
            return fail(f"missing_claim_field:{field}")
    if claim["receipt_version"] != "0.1":
        return fail("unsupported_version")
    if claim["receipt_role"] not in ("client_observed", "server_attested"):
        return fail("unsupported_receipt_role")

    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, Ed25519PublicKey):
            return fail("public_key_id_mismatch")
        public_der = public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    except (ImportError, TypeError, ValueError):
        return fail("public_key_id_mismatch")
    if receipt["public_key_id"] != sha256_bytes(public_der):
        return fail("public_key_id_mismatch")
    try:
        signature = base64.b64decode(receipt["signature"], validate=True)
        public_key.verify(signature, canonical_json_bytes(claim))
    except (InvalidSignature, ValueError, TypeError):
        return fail("invalid_signature")

    result: dict[str, Any] = {"ok": True}
    if artifact is not None:
        expected = claim.get("artifact_hash")
        actual = hash_file(artifact)
        result.update(
            artifact_ok=isinstance(expected, str) and expected == actual,
            expected_artifact_hash=expected,
            actual_artifact_hash=actual,
        )
    return result
