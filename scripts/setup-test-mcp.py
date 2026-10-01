#!/usr/bin/env python3
"""Register the local test MCP with Codex without replacing other settings."""
import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Run driver and MCP integration checks after installation")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    node = shutil.which("node") or "/home/serveperry/.nvm/versions/node/v20.20.2/bin/node"
    codex = shutil.which("codex")
    if not codex or not Path(node).is_file():
        parser.error("Codex and Node 20+ must be installed on this host.")
    node = str(Path(node).resolve())
    server = root / "scripts/test-mcp.cjs"
    if not (root / "target/debug/valhalla-server").is_file():
        parser.error("Build the test server first: bash scripts/cargo.sh build --locked")
    # Check dependencies before making any user-level configuration changes.
    subprocess.run([node, "-e", "require('@modelcontextprotocol/sdk/server/mcp.js'); require('ws'); require('zod');"], cwd=root, check=True)
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    original = config.read_text() if config.exists() else ""
    tomllib.loads(original)
    if config.exists():
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = config.with_name(f"config.toml.valhallasc-{stamp}.bak")
        backup.write_text(original)
        backup.chmod(0o600)
        print(f"Configuration backup: {backup}", flush=True)
    subprocess.run([codex, "mcp", "add", "valhallasc-testing", "--", node, str(server)], check=True)
    # The add command preserves other servers and settings. Set timeouts only
    # inside this server's table; scenarios involve real-time walking/combat.
    content = config.read_text()
    header = re.search(r"^\[mcp_servers\.valhallasc-testing\]\s*$", content, re.MULTILINE)
    if not header:
        raise RuntimeError("Codex did not write the expected MCP configuration table.")
    following = re.search(r"^\[", content[header.end():], re.MULTILINE)
    end = header.end() + following.start() if following else len(content)
    section = content[header.end():end]
    for key, value in [("startup_timeout_sec", 20), ("tool_timeout_sec", 180)]:
        section = re.sub(rf"^{key}\s*=.*\n?", "", section, flags=re.MULTILINE)
        section = section.rstrip() + f"\n{key} = {value}\n"
    content = content[:header.end()] + section + "\n" + content[end:]
    registered = tomllib.loads(content)["mcp_servers"]["valhallasc-testing"]
    if registered["command"] != node or registered["args"] != [str(server)]:
        raise RuntimeError("MCP launch configuration does not match this checkout.")
    config.write_text(content)
    print(f"Registered valhallasc-testing in {config}; tool timeout: 180 seconds.", flush=True)
    if args.verify:
        subprocess.run([node, "--test", "tests/test-driver.cjs"], cwd=root, check=True)
        print("Verified MCP handshake, all nine tools, private worlds, normal actions, a scenario, and cleanup.", flush=True)
    print("Restart Codex to load the registered tools into its tool catalog.", flush=True)


if __name__ == "__main__":
    main()
