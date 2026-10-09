"""Run the local Python and browser suites, owning and cleaning up the test server."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def run(*command, env=None):
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-only', action='store_true')
    args = parser.parse_args()
    if not args.browser_only:
        run(sys.executable, '-m', 'unittest', 'discover', 'tests')
        for suite in ('verify_security_sanitization.py',
                      'test_sessions_and_eras.py', 'test_mcp_server.py',
                      'test_season_robustness.py'):
            run(sys.executable, f'tests/{suite}')
    # Refuse to test an unrelated or stale application on the browser suites' port.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 8080))
    with tempfile.TemporaryDirectory(prefix='simgent-tests-') as private_dir:
        env = dict(os.environ, PORT='8080', HOST='127.0.0.1',
                   SIMGENT_RUNTIME_DIR=private_dir, LLM_PROVIDER='local',
                   GROQ_API_KEY='', GEMINI_API_KEY='', SIMGENT_ADMIN_TOKEN='')
        with open(Path(private_dir) / 'server.log', 'w+') as log:
            server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'frontend.main:app',
                                       '--host', '127.0.0.1', '--port', '8080'], cwd=ROOT,
                                      env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and server.poll() is None:
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(0.2)
                else:
                    log.seek(0)
                    raise RuntimeError('Test server failed to start:\n' + log.read())
                for suite in ('e2e_playwright_suite.js', 'test_mobile_replay_speed.js',
                              'test_albon_retirement_replay.js', 'test_starting_grid_replay.js'):
                    run('node', f'tests/{suite}', env=dict(os.environ, BASE_URL='http://localhost:8080'))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == '__main__':
    main()
