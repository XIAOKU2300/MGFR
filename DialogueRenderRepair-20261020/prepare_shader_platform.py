"""Align shader bundle with actual Linear/D3D11 player and retain stereo variants."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE, OUT = HERE / 'ShaderProject-v2', HERE / 'ShaderProject-v3'
OUT.mkdir(exist_ok=False)
for relative in ['Assets', 'Packages', 'ProjectSettings']:
    for path in (BASE / relative).rglob('*'):
        if not path.is_file() or path.suffix == '.meta' or path.name == 'packages-lock.json':
            continue
        if relative == 'ProjectSettings' and path.name != 'ProjectVersion.txt':
            continue
        data = path.read_bytes()
        if path.suffix in ['.shader', '.cs']:
            text = data.decode('utf-8')
            if path.suffix == '.shader':
                text = text.replace('#pragma multi_compile_instancing', '#pragma multi_compile_instancing\n#pragma multi_compile _ STEREO_INSTANCING_ON')
                text = text.replace('float facing:VFACE', 'bool facing:SV_IsFrontFace')
            else:
                text = text.replace('  AssetDatabase.Refresh();', '''  PlayerSettings.colorSpace=ColorSpace.Linear;
  PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);
  PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{UnityEngine.Rendering.GraphicsDeviceType.Direct3D11});
  PlayerSettings.stereoRenderingPath=StereoRenderingPath.Instancing;
  AssetDatabase.Refresh();''')
                text = text.replace('ShaderBundle-v2', 'ShaderBundle-v3')
            data = text.encode('utf-8')
        target = OUT / path.relative_to(BASE)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
print('LINEAR_STEREO_SHADER_PROJECT', OUT)
