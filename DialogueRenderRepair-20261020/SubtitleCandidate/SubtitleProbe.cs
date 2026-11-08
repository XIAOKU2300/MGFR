using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using MGFR.Dialogue;
using MGFR.Repairs;

public static class SubtitleProbe
{
    [Serializable] public class Report
    {
        public bool pass, oldGreenContaminationReproduced, repairedKeyGreenCorner, nonKeyMatchesOriginal, atlasPreserved, shaderCompiled;
        public int oldContaminatedPixels, repairedContaminatedPixels, oldForegroundPixels, repairedForegroundPixels, maxNonKeyChannelError, boundMaterials;
        public string source="actual CameraChatOverlay geometry and Microsoft YaHei font atlas; desktop render, no headset";
    }
    public static void Run()
    {
        int exit=1;
        try
        {
            string output=Path.GetFullPath(Path.Combine(Application.dataPath,"../../PixelProbe-v1"));
            if(Directory.Exists(output)) throw new Exception("Refuse existing pixel output");
            Directory.CreateDirectory(output);
            var report=new Report();
            QualitySettings.antiAliasing=0;
            var camera=new GameObject("Probe camera").AddComponent<Camera>();camera.tag="MainCamera";
            camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.green;camera.fieldOfView=40;camera.allowMSAA=false;camera.allowHDR=false;
            camera.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
            var rt=new RenderTexture(1024,768,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.Linear);rt.antiAliasing=1;rt.Create();camera.targetTexture=rt;
            var overlay=new GameObject("Actual conversation subtitles").AddComponent<CameraChatOverlay>();
            var flags=BindingFlags.NonPublic|BindingFlags.Instance;
            if(typeof(CameraChatOverlay).GetField("textMaterial",flags).GetValue(overlay)==null)
                typeof(CameraChatOverlay).GetMethod("Awake",flags).Invoke(overlay,null);
            typeof(CameraChatOverlay).GetMethod("LateUpdate",flags).Invoke(overlay,null);
            overlay.ShowReview("第二句话识别出来了吗？","看字幕的半透明背景，以及中文边缘。");
            Color32[] Render(string name)
            {
                camera.Render();RenderTexture.active=rt;var t=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false,true);t.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);t.Apply();
                File.WriteAllBytes(Path.Combine(output,name+".png"),t.EncodeToPNG());var pixels=t.GetPixels32();UnityEngine.Object.DestroyImmediate(t);return pixels;
            }
            int Foreground(Color32[] p){int n=0;foreach(var c in p)if(!(c.r==0&&c.g==255&&c.b==0))n++;return n;}
            int Contaminated(Color32[] p){int n=0;foreach(var c in p)if(c.g>c.r*1.35f&&c.g>c.b*1.35f&&!(c.r==0&&c.g==255&&c.b==0))n++;return n;}
            var old=Render("01-original-green");report.oldContaminatedPixels=Contaminated(old);report.oldForegroundPixels=Foreground(old);
            camera.backgroundColor=new Color(.13f,.15f,.19f);var normal=Render("02-original-nonkey");
            var textMaterial=(Material)typeof(CameraChatOverlay).GetField("textMaterial",flags).GetValue(overlay);var atlas=textMaterial.mainTexture;
            var repair=new GameObject("Subtitle composite repair").AddComponent<SubtitleChromaRepair>();
            var shader=Shader.Find("MGFR/ChatOverlayChroma");report.shaderCompiled=shader!=null&&shader.isSupported&&!UnityEditor.ShaderUtil.ShaderHasError(shader);
            repair.Initialize(shader);report.boundMaterials=repair.MaterialCount;report.atlasPreserved=textMaterial.mainTexture==atlas;
            repair.ConfigureForCamera(camera);var normalAfter=Render("03-repaired-nonkey");
            int max=0;for(int i=0;i<normal.Length;i++){max=Math.Max(max,Math.Abs(normal[i].r-normalAfter[i].r));max=Math.Max(max,Math.Abs(normal[i].g-normalAfter[i].g));max=Math.Max(max,Math.Abs(normal[i].b-normalAfter[i].b));}
            report.maxNonKeyChannelError=max;report.nonKeyMatchesOriginal=max<=1;
            camera.backgroundColor=Color.green;repair.ConfigureForCamera(camera);var fixedPixels=Render("04-repaired-green");
            report.repairedContaminatedPixels=Contaminated(fixedPixels);report.repairedForegroundPixels=Foreground(fixedPixels);
            report.repairedKeyGreenCorner=fixedPixels[0].r==0&&fixedPixels[0].g==255&&fixedPixels[0].b==0;
            report.oldGreenContaminationReproduced=report.oldContaminatedPixels>10000;
            report.pass=report.shaderCompiled&&report.oldGreenContaminationReproduced&&report.repairedContaminatedPixels==0&&report.repairedForegroundPixels>10000&&report.repairedKeyGreenCorner&&report.nonKeyMatchesOriginal&&report.atlasPreserved&&report.boundMaterials==2;
            File.WriteAllText(Path.Combine(output,"result.json"),JsonUtility.ToJson(report,true));
            var bundleDir=Path.Combine(output,"Bundle");Directory.CreateDirectory(bundleDir);
            BuildPipeline.BuildAssetBundles(bundleDir,new[]{new AssetBundleBuild{assetBundleName="subtitle_chroma",assetNames=new[]{"Assets/ChatOverlayChroma.shader"}}},BuildAssetBundleOptions.ForceRebuildAssetBundle,BuildTarget.StandaloneWindows64);
            if(!report.pass)throw new Exception("Subtitle pixel acceptance failed; see result.json");
            Debug.Log("SUBTITLE_PIXEL_PROBE_PASS");exit=0;
        }
        catch(Exception e){Debug.LogError(e.GetType().Name+": "+e.Message);}
        EditorApplication.Exit(exit);
    }
}
