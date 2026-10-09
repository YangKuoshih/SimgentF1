"""Archive a release tag and record its exact cleaned source commit."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    tag = os.environ['RELEASE_TAG']
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag):
        raise ValueError('Expected a vMAJOR.MINOR.PATCH release tag')
    commit = subprocess.check_output(['git', 'rev-parse', f'refs/tags/{tag}^{{commit}}'], text=True).strip()
    out = Path('release-artifacts')
    out.mkdir(exist_ok=True)
    archive = out / f'f1-simgent-{tag}.tar.gz'
    subprocess.run(['git', 'archive', '--format=tar.gz', f'--prefix=f1-simgent-{tag}/',
                    f'--output={archive}', commit], check=True)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / f'{archive.name}.sha256').write_text(f'{checksum}  {archive.name}\n')
    repo = os.environ['GITHUB_REPOSITORY']
    workflow = f'https://github.com/{repo}/.github/workflows/release.yml'
    predicate = {
        'buildDefinition': {
            'buildType': 'https://github.com/YangKuoshih/SimgentF1/source-archive/v1',
            'externalParameters': {'tag': tag},
            'internalParameters': {},
            'resolvedDependencies': [{'uri': f'git+https://github.com/{repo}@refs/tags/{tag}',
                                      'digest': {'gitCommit': commit}}]},
        'runDetails': {
            'builder': {'id': workflow},
            'metadata': {'invocationId': f"https://github.com/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"}}}
    (out / 'provenance.json').write_text(json.dumps(predicate, indent=2)+'\n')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'archive={archive}\ntag={tag}\ncommit={commit}\n')


if __name__ == '__main__':
    main()
