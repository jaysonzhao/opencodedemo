#!/usr/bin/env python3
"""Create/update OpenCode provider credentials without writing them to disk."""

import argparse
import base64
import json
import pathlib
import secrets
import subprocess


def save(namespace: str, name: str, values: dict[str, str], *, create: bool = False) -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": namespace},
        "type": "Opaque",
        "data": {
            key: base64.b64encode(value.encode()).decode()
            for key, value in values.items()
        },
    }
    command = (
        ["oc", "create", "-f", "-"]
        if create
        else [
            "oc",
            "apply",
            "--server-side",
            "--field-manager=opencode-setup",
            "-f",
            "-",
        ]
    )
    subprocess.run(command, input=json.dumps(manifest), text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="opencode")
    parser.add_argument(
        "--key-file", type=pathlib.Path, default=pathlib.Path.home() / "work/minimax.key"
    )
    args = parser.parse_args()

    key_path = args.key_file.expanduser()
    api_key = key_path.read_text().strip()
    if not api_key:
        raise SystemExit(f"MiniMax key file is empty: {key_path}")

    provider = {
        "BASE_URL": "https://api.minimax.io/v1",
        "PROVIDER_ID": "minimax-openai",
        "MODEL_NAME": "MiniMax-M2.7-highspeed",
        "MODEL_CONTEXT": "204800",
        "MODEL_OUTPUT": "8192",
        "API_KEY": api_key,
    }
    save(args.namespace, "opencode-provider", provider)

    existing = subprocess.run(
        [
            "oc",
            "-n",
            args.namespace,
            "get",
            "secret",
            "opencode-server-auth",
            "--ignore-not-found",
            "-o",
            "name",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not existing:
        save(
            args.namespace,
            "opencode-server-auth",
            {
                "OPENCODE_SERVER_USERNAME": "opencode",
                "OPENCODE_SERVER_PASSWORD": secrets.token_urlsafe(32),
            },
            create=True,
        )


if __name__ == "__main__":
    main()
