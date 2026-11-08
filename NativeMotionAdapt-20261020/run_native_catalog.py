from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'run_native_review.py').read_text(encoding='utf-8')
source=source.replace("default='native-v1'","default='Main'").replace("'-mgfr-native-review'","'-mgfr-native-catalog'").replace('timeout=150','timeout=240').replace("'acceptance-'","'catalog-'")
exec(compile(source,str(Path(__file__).resolve()),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})
