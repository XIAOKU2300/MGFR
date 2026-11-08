from pathlib import Path
root = Path(__file__).resolve().parent
project = root / 'GpuProbe-v1'
source = (project / 'Assets/Editor/StereoGpuProbeV2.cs').read_text(encoding='utf-8')
source = source.replace('StereoGpuProbeV2', 'StereoGpuProbeV3').replace('Probe-baseline-v2', 'Probe-baseline-v3')
source = source.replace('RenderTextureFormat.ARGB32,0)', 'RenderTextureFormat.ARGB32,24)')
source = source.replace('ClearRenderTarget(false,true,Color.green)', 'ClearRenderTarget(true,true,Color.green)')
source = source.replace('command.EnableShaderKeyword("STEREO_INSTANCING_ON");', 'command.SetSinglePassStereo(SinglePassStereoMode.Instancing);command.EnableShaderKeyword("STEREO_INSTANCING_ON");')
source = source.replace('command.DisableShaderKeyword("STEREO_INSTANCING_ON");', 'command.SetSinglePassStereo(SinglePassStereoMode.None);command.DisableShaderKeyword("STEREO_INSTANCING_ON");')
with (project / 'Assets/Editor/StereoGpuProbeV3.cs').open('x', encoding='utf-8') as f:
    f.write(source)
print('Prepared depth-enabled stereo probe.')
