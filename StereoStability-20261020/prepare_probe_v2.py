from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE/'GpuProbe-v1'
source=(PROJECT/'Assets/Editor/StereoGpuProbe.cs').read_text(encoding='utf-8')
source=source.replace('public static class StereoGpuProbe {','public static class StereoGpuProbeV2 {').replace('Probe-baseline-v1','Probe-baseline-v2')
source=source.replace('foreach(var shader in bundle.LoadAllAssets<Shader>()){','''
  var stereoBytes=new float[272];for(int matrix=0;matrix<16;matrix++)for(int d=0;d<4;d++)stereoBytes[matrix*16+d*5]=1;
  stereoBytes[258]=-2;stereoBytes[262]=-2;stereoBytes[264]=stereoBytes[265]=stereoBytes[268]=stereoBytes[269]=1;
  var stereoBuffer=new ComputeBuffer(68,16,ComputeBufferType.Constant);stereoBuffer.SetData(stereoBytes);
  foreach(var shader in bundle.LoadAllAssets<Shader>()){''')
source=source.replace('command.EnableShaderKeyword("STEREO_INSTANCING_ON");command.DrawMeshInstanced', 'command.EnableShaderKeyword("STEREO_INSTANCING_ON");command.SetGlobalConstantBuffer(stereoBuffer,Shader.PropertyToID("UnityStereoGlobals"),0,1088);command.DrawMeshInstanced')
source=source.replace('result.rows=rows.ToArray();','stereoBuffer.Release();result.rows=rows.ToArray();')
with (PROJECT/'Assets/Editor/StereoGpuProbeV2.cs').open('x',encoding='utf-8') as f:f.write(source)
print('Prepared stereo GPU constant-buffer probe.')
