"""Fail CI if the compatibility dependency input drifts from project metadata."""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
compatibility = {
    line.strip() for line in (ROOT / 'requirements.in').read_text().splitlines()
    if line.strip() and not line.lstrip().startswith('#')
}
assert set(project['project']['dependencies']) == compatibility, (
    'Keep requirements.in and pyproject.toml dependencies consistent before regenerating the hash lock.'
)
print('Python dependency metadata is consistent.')
