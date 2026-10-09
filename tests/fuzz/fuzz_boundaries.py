"""Coverage-guided fuzzing with synthetic inputs; no network or runtime writes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Also runnable without Atheris as a deterministic corpus smoke check.
from app.tools import guardrails as G
from app.tools import jolpica_sync as J


def test_one_input(data):
    text = data.decode('utf-8', errors='replace')
    clean = G.sanitize_input(text)
    assert isinstance(clean, str) and len(clean) <= 500
    assert '\x00' not in clean
    for check in (G.check_prompt_injection, G.check_dangerous_content,
                  G.check_out_of_scope, G.check_unsupported_data):
        blocked, message = check(clean)
        assert isinstance(blocked, bool)
        assert message is None or isinstance(message, str)
    card = G.sanitize_a2ui_card({'title': text, 'metrics': [
        {'label': text, 'value': text, 'color': text}], 'target': {'year': text}})
    assert '<' not in card['title'] and '<' not in card['metrics'][0]['value']
    try:
        path = J._path(text)
    except ValueError:
        pass
    else:
        assert Path(path).parent == Path(J.CACHE)


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        for seed in (Path(__file__).parent / 'corpus').iterdir():
            test_one_input(seed.read_bytes())
        for seed in (b'', bytes(range(256)), b'9' * 10000, b'<td>' * 2000):
            test_one_input(seed)
        print('Synthetic fuzz corpus smoke checks passed.')
    else:
        import atheris
        atheris.instrument_all()
        atheris.Setup(sys.argv, test_one_input)
        atheris.Fuzz()
