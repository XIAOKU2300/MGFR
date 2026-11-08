from pathlib import Path

script = Path(__file__).with_name('analyze.py')
code = script.read_text(encoding='utf8')
old = "out = lab / 'Review'"
assert code.count(old) == 1
exec(compile(code.replace(old, "out = lab / 'ReviewSwimsuit'"), str(script), 'exec'),
     {'__file__': str(script), '__name__': '__main__'})
