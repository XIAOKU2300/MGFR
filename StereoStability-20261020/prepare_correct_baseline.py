from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeV4.cs').read_text(encoding='utf-8')
source=source.replace('StereoGpuProbeV4','StereoGpuProbeOldPackage').replace('Probe-retained-v2','Probe-old-package')
source=source.replace('H:/MGFR/StereoStability-20261020/Bundle-retained-v2/mgfr-mr-coverage','H:/MGFR/DialogueRenderRepair-20261020/Final-v3/Player/MGFR_Data/StreamingAssets/mgfr-mr-coverage')
with (root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeOldPackage.cs').open('x',encoding='utf-8') as f:f.write(source)
print('Prepared old-package comparison with the same corrected draw path.')
