"""Stage one current-runtime module update and a private verification player."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=HERE/'Player'
SOURCE=HERE/'Source'

def create(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(data.encode('utf-8') if isinstance(data,str) else data)

def prepare_shader():
    project=HERE/'MenuBuild/ShaderProject-v1'
    project.mkdir(parents=True,exist_ok=False)
    create(project/'ProjectSettings/ProjectVersion.txt','m_EditorVersion: 6000.3.26f1\n')
    create(project/'Packages/manifest.json',json.dumps({'dependencies':{'com.unity.modules.assetbundle':'1.0.0'}}))
    for name in ['GesturePanel.shader','GesturePanelText.shader']:create(project/'Assets'/name,(SOURCE/'GesturePanel'/name).read_bytes())
    editor='''using System;using System.IO;using System.Linq;using UnityEngine;using UnityEditor;
public static class HandPanelShaders {
 public static void Build(){
  PlayerSettings.colorSpace=ColorSpace.Linear;PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{UnityEngine.Rendering.GraphicsDeviceType.Direct3D11});PlayerSettings.stereoRenderingPath=StereoRenderingPath.Instancing;
  AssetDatabase.Refresh();var paths=AssetDatabase.FindAssets("t:Shader").Select(AssetDatabase.GUIDToAssetPath).ToArray();string output=Path.Combine(Directory.GetParent(Application.dataPath).Parent.FullName,"Bundle-v1");if(Directory.Exists(output))throw new Exception("Output exists");Directory.CreateDirectory(output);
  if(BuildPipeline.BuildAssetBundles(output,new[]{new AssetBundleBuild{assetBundleName="gesture-touch-panel-v1",assetNames=paths}},BuildAssetBundleOptions.ForceRebuildAssetBundle,BuildTarget.StandaloneWindows64)==null)throw new Exception("Build failed");
  foreach(string path in paths){var shader=AssetDatabase.LoadAssetAtPath<Shader>(path);foreach(var m in ShaderUtil.GetShaderMessages(shader))if(m.severity.ToString()=="Error")throw new Exception("Shader compile failed: "+m.message);}
  Debug.Log("HAND_PANEL_SHADER_BUNDLE_PASS");
 }
}'''
    create(project/'Assets/Editor/HandPanelShaders.cs',editor)
    print('NEW_PANEL_SHADER_PROJECT',project,flush=True)

def stage(name):
    if not name.startswith('Preview-v') or not name[9:].isdigit():raise ValueError('Expected Preview-v plus an integer')
    out=HERE/'MenuBuild'/name;out.mkdir(parents=True,exist_ok=False)
    src=out/'Source';src.mkdir()
    for path in SOURCE.rglob('*.cs'):
        text=path.read_text(encoding='utf-8')
        if path.name=='NativeAvatarActions-main.cs':
            before='public static void Install(){MGFR.Repairs.MrClothCoverageRepair.Install();'
            assert text.count(before)==1
            hook='MGFR.GesturePanel.GesturePanelRuntime.Install();'
            assert text.count(hook)<=1
            if hook not in text:text=text.replace(before,before+hook)
        create(src/path.relative_to(SOURCE),text)
    managed=BASE/'MGFR_Data/Managed';work=out/'Build';work.mkdir();plugin=work/'MGFR.StructuredVoiceFinal.dll'
    options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(plugin)]
    options+=['/reference:'+str(path) for path in managed.glob('*.dll') if path.name!=plugin.name]
    options+=[str(path) for path in src.rglob('*.cs')]
    rsp=work/'compile.rsp';create(rsp,'\n'.join('"'+x+'"' for x in options))
    subprocess.run([str(ROOT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(ROOT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(rsp)],check=True)
    for path in BASE.rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(BASE)
        if relative.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb','MGFR_Data/StreamingAssets/gesture-touch-panel-v1']:continue
        create(out/'Player'/relative,path.read_bytes())
    create(out/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll',plugin.read_bytes())
    active_bundle=BASE/'MGFR_Data/StreamingAssets/gesture-touch-panel-v1'
    create(out/'Player/MGFR_Data/StreamingAssets/gesture-touch-panel-v1',(active_bundle if active_bundle.is_file() else HERE/'MenuBuild/Bundle-v1/gesture-touch-panel-v1').read_bytes())
    create(out/'receipt.json',json.dumps({'activePlayer':str(BASE/'MGFR.exe'),'moduleSha256':hashlib.sha256(plugin.read_bytes()).hexdigest(),'entryUnchanged':True,'voiceUnchanged':True},indent=2))
    print('CURRENT_RUNTIME_MENU_CANDIDATE',out,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--shader-project',action='store_true');parser.add_argument('--name',default='Preview-v1');args=parser.parse_args()
    if args.shader_project:prepare_shader()
    else:stage(args.name)
