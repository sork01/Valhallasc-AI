"""Install the prepared scoped HTTPS proxy and a user service; run from this repo.

Requires host Docker access and writes the host vhost source/user service. Checks
the reviewed baseline before touching it, keeps backups, validates Apache before
a graceful reload, and rolls back the proxy if installation fails.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / 'deploy'
HOST_CONFIG = ROOT.parent.parent / '000-default.conf'
CONTAINER_CONFIG = '/etc/apache2/sites-available/000-default.conf'
UNIT = Path.home() / '.config/systemd/user/valhalla.service'
INCLUDE = '  Include /var/www/Valhallasc/deploy/apache.conf\n'


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def docker_config():
    return run('docker', 'exec', 'php8site', 'cat', CONTAINER_CONFIG,
               capture_output=True).stdout


def health():
    with urllib.request.urlopen('http://172.18.0.1:8080/health', timeout=3) as r:
        return json.load(r)


def main():
    candidate = (DEPLOY / '000-default.conf.proposed').read_text()
    expected = (DEPLOY / 'apache-baseline.sha256').read_text().strip()
    current = docker_config()
    assert hashlib.sha256(current.encode()).hexdigest() == expected, 'Active Apache config changed since review; re-stage the patch.'
    assert HOST_CONFIG.read_text() == current, 'Host Apache source differs from active container config.'
    assert candidate.replace(INCLUDE, '', 1) == current, 'Candidate must only add the scoped Valhalla include.'
    assert not UNIT.exists(), 'A Valhalla service already exists; inspect it before replacing.'
    assert (ROOT / 'target/release/valhalla-server').is_file(), 'Build release server first.'

    backup = DEPLOY / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(parents=True)
    (backup / '000-default.conf').write_text(current)
    # Stop only the development process belonging to this project, allowing it
    # to save gracefully before the managed service opens the same database.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if (proc / 'cwd').resolve() != ROOT:
                continue
            executable = (proc / 'exe').resolve()
            if executable not in [ROOT / 'target/debug/valhalla-server', ROOT / 'target/release/valhalla-server']:
                continue
            os.kill(int(proc.name), signal.SIGTERM)
            for _ in range(100):
                if not (proc / 'exe').exists():
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError('Development server did not stop gracefully.')
        except (FileNotFoundError, PermissionError):
            continue

    changed_proxy = False
    installed_unit = False
    try:
        UNIT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEPLOY / 'valhalla.service', UNIT)
        installed_unit = True
        run('systemctl', '--user', 'daemon-reload')
        run('systemctl', '--user', 'enable', '--now', 'valhalla.service')
        for _ in range(40):
            try:
                if health()['status'] == 'ok':
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError('Managed Rust server failed its health check.')
        run('docker', 'exec', 'php8site', 'curl', '--fail', '--silent', 'http://172.18.0.1:8080/health')
        run('docker', 'exec', 'php8site', 'apache2ctl', '-t', '-c', 'Include /var/www/Valhallasc/deploy/apache.conf')
        HOST_CONFIG.write_text(candidate)
        changed_proxy = True
        run('docker', 'cp', str(HOST_CONFIG), f'php8site:{CONTAINER_CONFIG}')
        run('docker', 'exec', 'php8site', 'apache2ctl', '-t')
        run('docker', 'exec', 'php8site', 'apache2ctl', 'graceful')
        run('systemctl', '--user', 'is-active', 'valhalla.service')
        print('\nInstalled: https://gunning.se/Valhallasc/')
        print(f'Apache config backup: {backup}')
    except Exception:
        if changed_proxy:
            HOST_CONFIG.write_text(current)
            run('docker', 'cp', str(HOST_CONFIG), f'php8site:{CONTAINER_CONFIG}')
            run('docker', 'exec', 'php8site', 'apache2ctl', '-t')
            run('docker', 'exec', 'php8site', 'apache2ctl', 'graceful')
        if installed_unit:
            run('systemctl', '--user', 'disable', '--now', 'valhalla.service')
            UNIT.unlink(missing_ok=True)
            run('systemctl', '--user', 'daemon-reload')
        raise


if __name__ == '__main__':
    main()
