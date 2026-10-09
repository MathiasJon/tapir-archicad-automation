#!/usr/bin/env python3
"""Opens every BIMcloud/Teamwork-sourced hotlink module of the currently
open project, each in its own new Archicad instance.

Requires: a running Archicad with the Tapir Add-On, reachable on the given port.
Run with: python3 open_bimcloud_hotlinks.py [--port 19723] [--dry-run]
"""
import argparse
import subprocess
import sys
import urllib.request
import json


def execute_command(port: int, command_name: str, parameters: dict | None = None) -> dict:
    url = f"http://127.0.0.1:{port}"
    payload = {
        "command": "API.ExecuteAddOnCommand",
        "parameters": {
            "addOnCommandId": {"commandNamespace": "TapirCommand", "commandName": command_name},
            "addOnCommandParameters": parameters or {},
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("succeeded"):
        raise RuntimeError(f"{command_name} failed: {result}")
    return result["result"]["addOnCommandResponse"]


def collect_teamwork_module_locations(nodes: list) -> list[str]:
    locations = []
    for node in nodes:
        if node.get("type") == "Module" and node.get("location", "").startswith("teamwork://"):
            locations.append(node["location"])
        locations.extend(collect_teamwork_module_locations(node.get("children", [])))
    return locations


def open_in_new_instance(archicad_app_path: str, teamwork_url: str, dry_run: bool) -> None:
    # macOS only: -n forces a new instance even if Archicad is already running.
    cmd = ["open", "-n", archicad_app_path, "--args", "-openasplan", teamwork_url]
    if dry_run:
        # Redact the token before printing.
        redacted = teamwork_url.split("@", 1)
        redacted_url = "teamwork://<redacted>@" + redacted[1] if len(redacted) == 2 else "<redacted>"
        print("Would run:", " ".join(cmd[:-1] + [redacted_url]))
        return
    subprocess.Popen(cmd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=19723)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    archicad_location = execute_command(args.port, "GetArchicadLocation")["archicadLocation"]
    hotlinks = execute_command(args.port, "GetHotlinks")["hotlinks"]
    teamwork_locations = collect_teamwork_module_locations(hotlinks)

    if not teamwork_locations:
        print("No BIMcloud-sourced hotlink modules found in the current project.")
        return 0

    print(f"Found {len(teamwork_locations)} BIMcloud-sourced module(s). Opening...")
    for location in teamwork_locations:
        open_in_new_instance(archicad_location, location, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
