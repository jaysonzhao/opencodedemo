#!/usr/bin/env python3
"""Pin the latest validated OpenShift ImageStream digest in both manifests."""

import argparse
import pathlib
import re
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="opencode")
    args = parser.parse_args()

    ref = subprocess.check_output(
        [
            "oc",
            "-n",
            args.namespace,
            "get",
            "istag",
            "opencode-server:validated",
            "-o",
            "jsonpath={.image.dockerImageReference}",
        ],
        text=True,
    ).strip()
    if not re.search(r"@sha256:[0-9a-f]{64}$", ref):
        raise SystemExit("ImageStreamTag did not return a digest-pinned image reference")

    root = pathlib.Path(__file__).resolve().parents[1]
    pattern = re.compile(
        r"(?m)^(\s*image:\s*)\S*opencode-server@sha256:[0-9a-f]{64}(\s*)$"
    )
    for relative in (
        "opencode-server-build/workload.yaml",
        "opencode-server-build/client.yaml",
    ):
        path = root / relative
        text = path.read_text()
        updated, count = pattern.subn(lambda m: m.group(1) + ref + m.group(2), text)
        if count != 1:
            raise SystemExit(f"Expected one image reference in {path}, found {count}")
        path.write_text(updated)
    print("Updated workload and smoke-test manifests to the validated image digest.")


if __name__ == "__main__":
    main()
