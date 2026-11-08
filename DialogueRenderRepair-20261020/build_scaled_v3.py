from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'build_scaled_final.py').read_text(encoding='utf-8')
source=source.replace("OUT=HERE/'Final'","OUT=HERE/'Final-v3'")
source=source.replace("(HERE/'ClothScaleReview.cs').read_bytes()", "(HERE/'ClothScaleReview.cs').read_text(encoding='utf-8').replace('control.Position','control.PlanarPosition')")
source=source.replace('ResidualPenetration/=factor;', 'if(frames%30==0)ResidualPenetration/=factor;')
source=source.replace('Mathf.Abs(factor-1)>.00001f){', 'Mathf.Abs(factor-1)>.00001f&&Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-scale-old-metric")<0){')
exec(compile(source,str(HERE/'build_scaled_final.py'),'exec'),{'__file__':str(HERE/'build_scaled_final.py'),'__name__':'__main__'})
