"""Refine coverage alpha to one sample per 4:2:0 cell in a new shader project."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'ShaderProject-v1'
OUT = HERE / 'ShaderProject-v2'
OUT.mkdir(exist_ok=False)
for relative in ['Assets', 'Packages', 'ProjectSettings']:
    for path in (BASE / relative).rglob('*'):
        if not path.is_file() or path.suffix == '.meta' or path.name in ['packages-lock.json']:
            continue
        # Only authored files, not generated Unity editor settings.
        if relative == 'ProjectSettings' and path.name != 'ProjectVersion.txt':
            continue
        target = OUT / path.relative_to(BASE)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        if path.suffix in ('.shader', '.cginc', '.cs'):
            text = data.decode('utf-8')
            if path.name == 'RepairCoverage.cginc':
                text = text.replace('float MgfrCoverageAlpha', '''float2 MgfrCoverageUV(float2 uv, float2 pixel)
{
    float cell = max(2, _MGFRRgbKeyCoverageCell);
    float2 delta = (floor(pixel / cell) + .5) * cell - pixel;
    return uv + ddx(uv) * delta.x + ddy(uv) * delta.y;
}
float MgfrCoverageAlpha''')
            elif path.suffix == '.shader' and '/MrCoverage"' in text:
                if 'Zmd' in path.name or 'SiSwimsuit' in path.name:
                    text = text.replace('MgfrCoverageAlpha(alpha,i.positionCS.xy)', 'MgfrCoverageAlpha(_MGFRRgbKeyCoverage>.5 ? SAMPLE_TEXTURE2D(_BaseColor,sampler_BaseColor,MgfrCoverageUV(i.uv,i.positionCS.xy)).a*_TintColor.a*_Color.a : alpha,i.positionCS.xy)')
                else:
                    for alpha in ['c.a', 'base.a']:
                        text = text.replace('MgfrCoverageAlpha('+alpha+',i.pos.xy)', 'MgfrCoverageAlpha(_MGFRRgbKeyCoverage>.5 ? tex2D(_MainTex,MgfrCoverageUV(i.uv,i.pos.xy)).a*_Color.a : '+alpha+',i.pos.xy)')
            elif path.name == 'BuildRepairShaders.cs':
                text = text.replace('ShaderBundle-v1', 'ShaderBundle-v2')
            data = text.encode('utf-8')
        with target.open('xb') as stream:
            stream.write(data)
print('FINAL_SHADER_PROJECT', OUT)
