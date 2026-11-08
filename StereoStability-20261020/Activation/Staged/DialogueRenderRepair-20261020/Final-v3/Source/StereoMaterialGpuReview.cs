using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

using UnityEngine;
using UnityEngine.Rendering;
namespace MGFR.Repairs { public static class StereoMaterialGpuReview {
 [Serializable]class Row{public string shader;public float alpha;public bool keyCoverage;public int leftPixels,rightPixels,mismatchPixels;public bool supported;}
 [Serializable]class Report{public string source="D3D11 GPU instanced draw into two Texture2DArray slices; identical eye matrices, no headset";public bool canary,pass;public Row[] rows;}
 public static bool Run(string output){
  if(Directory.Exists(output))throw new Exception("GPU review output exists");Directory.CreateDirectory(output);
  var descriptor=new RenderTextureDescriptor(256,256,RenderTextureFormat.ARGB32,24){dimension=TextureDimension.Tex2DArray,volumeDepth=2,msaaSamples=1};var target=new RenderTexture(descriptor);target.Create();
  CommandBuffer command;var result=new Report();int[] counts;result.canary=target.IsCreated();
  var bundle=AssetBundle.GetAllLoadedAssetBundles().Single(b=>b.name=="mgfr-mr-coverage");
  var menuBundle=AssetBundle.GetAllLoadedAssetBundles().Single(b=>b.name=="gesture-touch-panel-v1");var rows=new List<Row>();
  var mesh=new Mesh();mesh.vertices=new[]{new Vector3(-.65f,-.65f,0),new Vector3(.65f,-.65f,0),new Vector3(.65f,.65f,0),new Vector3(-.65f,.65f,0)};mesh.uv=new[]{Vector2.zero,Vector2.right,Vector2.one,Vector2.up};mesh.normals=new[]{Vector3.back,Vector3.back,Vector3.back,Vector3.back};mesh.tangents=new[]{new Vector4(1,0,0,1),new Vector4(1,0,0,1),new Vector4(1,0,0,1),new Vector4(1,0,0,1)};mesh.colors=new[]{Color.white,Color.white,Color.white,Color.white};mesh.triangles=new[]{0,2,1,0,3,2};mesh.RecalculateBounds();
  
  var stereoBytes=new float[272];for(int matrix=0;matrix<16;matrix++)for(int d=0;d<4;d++)stereoBytes[matrix*16+d*5]=1;
  stereoBytes[258]=-2;stereoBytes[262]=-2;stereoBytes[264]=stereoBytes[265]=stereoBytes[268]=stereoBytes[269]=1;
  var stereoBuffer=new ComputeBuffer(68,16,ComputeBufferType.Constant);stereoBuffer.SetData(stereoBytes);
  foreach(var shader in bundle.LoadAllAssets<Shader>().Concat(menuBundle.LoadAllAssets<Shader>())) foreach(float alpha in new[]{1f,.42f}) foreach(bool key in new[]{false,true}) {
   mesh.colors=new[]{new Color(1,1,1,alpha),new Color(1,1,1,alpha),new Color(1,1,1,alpha),new Color(1,1,1,alpha)};var material=new Material(shader){enableInstancing=true};foreach(var p in new[]{"_Cull","_ZWrite"})if(material.HasProperty(p))material.SetFloat(p,0);foreach(var p in new[]{"_SrcBlend"})if(material.HasProperty(p))material.SetFloat(p,5);if(material.HasProperty("_DstBlend"))material.SetFloat("_DstBlend",10);foreach(var p in new[]{"_Color","_TintColor","_AmbientColor","_EmissionColor"})if(material.HasProperty(p))material.SetColor(p,Color.white);if(material.HasProperty("_Color"))material.SetColor("_Color",new Color(1,1,1,alpha));if(material.HasProperty("_AlphaClip"))material.SetFloat("_AlphaClip",.001f);if(material.HasProperty("_MainTex"))material.SetTexture("_MainTex",Texture2D.whiteTexture);if(material.HasProperty("_BaseColor"))material.SetTexture("_BaseColor",Texture2D.whiteTexture);
   command=new CommandBuffer();command.SetRenderTarget(target,0,CubemapFace.Unknown,-1);command.ClearRenderTarget(true,true,Color.green);command.SetViewProjectionMatrices(Matrix4x4.identity,Matrix4x4.identity);command.SetGlobalMatrixArray("unity_StereoMatrixVP",new[]{Matrix4x4.identity,Matrix4x4.identity});command.SetGlobalMatrixArray("unity_StereoMatrixV",new[]{Matrix4x4.identity,Matrix4x4.identity});command.SetGlobalMatrixArray("unity_StereoMatrixP",new[]{Matrix4x4.identity,Matrix4x4.identity});command.SetGlobalVectorArray("unity_StereoWorldSpaceCameraPos",new[]{new Vector4(0,0,-2,1),new Vector4(0,0,-2,1)});command.SetGlobalVector("_ZmdMainLightDirection",new Vector4(0,1,-1,0));command.SetGlobalVector("_ZmdMainLightColor",Vector4.one);command.SetGlobalVector("_ZmdAmbientColor",Vector4.one);command.SetGlobalFloat("_MGFRRgbKeyCoverage",key?1:0);command.SetGlobalFloat("_MGFRRgbKeyCoverageCell",2);command.SetSinglePassStereo(SinglePassStereoMode.Instancing);command.EnableShaderKeyword("STEREO_INSTANCING_ON");command.SetGlobalConstantBuffer(stereoBuffer,Shader.PropertyToID("UnityStereoGlobals"),0,1088);command.SetInstanceMultiplier(2);command.DrawMesh(mesh,Matrix4x4.identity,material,0,0);command.SetInstanceMultiplier(1);command.SetSinglePassStereo(SinglePassStereoMode.None);command.DisableShaderKeyword("STEREO_INSTANCING_ON");Graphics.ExecuteCommandBuffer(command);command.Release();
   counts=Read(target,output,shader.name.Replace('/','_')+"-"+alpha.ToString(System.Globalization.CultureInfo.InvariantCulture)+"-"+key);rows.Add(new Row{shader=shader.name,alpha=alpha,keyCoverage=key,supported=shader.isSupported,leftPixels=counts[0],rightPixels=counts[1],mismatchPixels=lastMismatch});UnityEngine.Object.DestroyImmediate(material);
  }
  stereoBuffer.Release();result.rows=rows.ToArray();result.pass=result.canary&&rows.Count==32&&rows.All(r=>r.supported&&r.leftPixels>100&&r.rightPixels>100&&r.mismatchPixels==0);using(var f=new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew))using(var w=new StreamWriter(f))w.Write(JsonUtility.ToJson(result,true));Debug.Log("STEREO_GPU_PROBE_COMPLETE "+result.pass);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(mesh);Shader.SetGlobalFloat("_MGFRRgbKeyCoverage",0);return result.pass;
 }
 static int lastMismatch;
 static int[] Read(RenderTexture target,string output,string name){var counts=new int[2];Color32[] left=null;lastMismatch=0;for(int eye=0;eye<2;eye++){Graphics.SetRenderTarget(target,0,CubemapFace.Unknown,eye);var image=new Texture2D(256,256,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,256,256),0,0);image.Apply();var pixels=image.GetPixels32();if(eye==0)left=pixels;else for(int i=0;i<pixels.Length;i++)if(left[i].r!=pixels[i].r||left[i].g!=pixels[i].g||left[i].b!=pixels[i].b)lastMismatch++;foreach(var p in pixels)if(!(p.g>250&&p.r<5&&p.b<5))counts[eye]++;using(var f=new FileStream(Path.Combine(output,name+"-"+eye+".png"),FileMode.CreateNew)){var bytes=image.EncodeToPNG();f.Write(bytes,0,bytes.Length);}UnityEngine.Object.DestroyImmediate(image);}RenderTexture.active=null;return counts;}
}

}
