from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'build_scaled_final.py').read_text(encoding='utf-8')
source=source.replace("OUT=HERE/'Final'","OUT=HERE/'Final-v2'")
source=source.replace("(HERE/'ClothScaleReview.cs').read_bytes()", "(HERE/'ClothScaleReview.cs').read_text(encoding='utf-8').replace('control.Position','control.PlanarPosition')")
exec(compile(source,str(HERE/'build_scaled_final.py'),'exec'),{'__file__':str(HERE/'build_scaled_final.py'),'__name__':'__main__'})
