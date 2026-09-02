#!/usr/bin/env python3
"""Verify a BoundaryAttest receipt with a caller-supplied expected public key."""

import argparse
import json
from pathlib import Path

from boundaryattest import verify_receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("public_key", type=Path)
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args()
    result = verify_receipt(
        args.receipt.read_text(encoding="utf-8"),
        args.public_key.read_bytes(),
        args.artifact,
    )
    print(json.dumps(result, separators=(",", ":")))
    raise SystemExit(0 if result["ok"] and result.get("artifact_ok", True) else 1)


if __name__ == "__main__":
    main()
