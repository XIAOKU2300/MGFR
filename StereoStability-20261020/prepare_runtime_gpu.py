from pathlib import Path
root=Path(__file__).resolve().parent
text=(root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeFinal.cs').read_text(encoding='utf-8')
text=text.replace('using UnityEditor;','')
text=text.replace('public static class StereoGpuProbeFinal {','namespace MGFR.Repairs { public static class StereoMaterialGpuReview {')
text=text.replace('public string shader;public int leftPixels,rightPixels;','public string shader;public float alpha;public bool keyCoverage;public int leftPixels,rightPixels,mismatchPixels;')
start=text.index(' public static void Run(){')
end=text.index('  var descriptor=',start)
text=text[:start]+''' public static bool Run(string output){
  if(Directory.Exists(output))throw new Exception("GPU review output exists");Directory.CreateDirectory(output);
'''+text[end:]
start=text.index('  var canary=')
end=text.index('  var mesh=',start)
text=text[:start]+'''  CommandBuffer command;var result=new Report();int[] counts;result.canary=target.IsCreated();
  var bundle=AssetBundle.GetAllLoadedAssetBundles().Single(b=>b.name=="mgfr-mr-coverage");
  var menuBundle=AssetBundle.GetAllLoadedAssetBundles().Single(b=>b.name=="gesture-touch-panel-v1");var rows=new List<Row>();
'''+text[end:]
text=text.replace('foreach(var shader in bundle.LoadAllAssets<Shader>().Concat(menuBundle.LoadAllAssets<Shader>())){','foreach(var shader in bundle.LoadAllAssets<Shader>().Concat(menuBundle.LoadAllAssets<Shader>())) foreach(float alpha in new[]{1f,.42f}) foreach(bool key in new[]{false,true}) {')
text=text.replace('var material=new Material(shader){enableInstancing=true};','mesh.colors=new[]{new Color(1,1,1,alpha),new Color(1,1,1,alpha),new Color(1,1,1,alpha),new Color(1,1,1,alpha)};var material=new Material(shader){enableInstancing=true};')
text=text.replace('material.SetFloat(p,1);','material.SetFloat(p,5);').replace('material.SetFloat("_DstBlend",0);','material.SetFloat("_DstBlend",10);')
text=text.replace('material.SetColor(p,Color.white);','material.SetColor(p,Color.white);if(material.HasProperty("_Color"))material.SetColor("_Color",new Color(1,1,1,alpha));')
text=text.replace('command.SetGlobalFloat("_MGFRRgbKeyCoverage",1);','command.SetGlobalFloat("_MGFRRgbKeyCoverage",key?1:0);')
text=text.replace('counts=Read(target,output,shader.name.Replace(\'/\',\'_\'));rows.Add(new Row{shader=shader.name,supported=shader.isSupported,leftPixels=counts[0],rightPixels=counts[1]});','counts=Read(target,output,shader.name.Replace(\'/\',\'_\')+"-"+alpha.ToString(System.Globalization.CultureInfo.InvariantCulture)+"-"+key);rows.Add(new Row{shader=shader.name,alpha=alpha,keyCoverage=key,supported=shader.isSupported,leftPixels=counts[0],rightPixels=counts[1],mismatchPixels=lastMismatch});')
text=text.replace('result.canary&&rows.All(r=>r.leftPixels>100&&r.rightPixels>100&&Math.Abs(r.leftPixels-r.rightPixels)<50)','result.canary&&rows.Count==32&&rows.All(r=>r.supported&&r.leftPixels>100&&r.rightPixels>100&&r.mismatchPixels==0)')
text=text.replace('target.Release();','target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(mesh);Shader.SetGlobalFloat("_MGFRRgbKeyCoverage",0);return result.pass;')
text=text.replace(' static int[] Read(', ' static int lastMismatch;\n static int[] Read(')
text=text.replace('var counts=new int[2];for(int eye=0;','var counts=new int[2];Color32[] left=null;lastMismatch=0;for(int eye=0;')
text=text.replace('foreach(var p in image.GetPixels32())','var pixels=image.GetPixels32();if(eye==0)left=pixels;else for(int i=0;i<pixels.Length;i++)if(left[i].r!=pixels[i].r||left[i].g!=pixels[i].g||left[i].b!=pixels[i].b)lastMismatch++;foreach(var p in pixels)')
text+='\n}\n'
with (root/'StereoMaterialGpuReview.cs').open('x',encoding='utf-8') as f:f.write(text)
print('Prepared runtime GPU review, 32 stereo comparisons.')
