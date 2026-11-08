from pathlib import Path
HERE = Path(__file__).resolve().parent
source = (HERE / 'build_repair_release.py').read_text(encoding='utf-8')
source = source.replace("OUT = HERE / 'Release-v1'", "OUT = HERE / 'Current'")
source = source.replace('ShaderBundle-v2', 'ShaderBundle-v4')
exec(compile(source, str(HERE / 'build_repair_release.py'), 'exec'), {'__file__': str(HERE / 'build_repair_release.py'), '__name__': '__main__'})
