from pathlib import Path
import subprocess
import os
HERE=Path(__file__).resolve().parent
FINAL=HERE.parents[1]

def write(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b.encode('utf-8') if isinstance(b,str) else b)

text=(HERE/'FootSourceReview.cs').read_text(encoding='utf-8')
text=text.replace('part.SetActive(false);}', 'part.SetActive(false);live.Cloth.SetWardrobeMesh(live.Adapter.VisibleMesh);}')
text=text.replace('for(int i=0;i<rest.Length;i++)if(rest[i].y<.08f)', 'var visible=new HashSet<int>();for(int s=0;s<renderer.sharedMesh.subMeshCount;s++)foreach(int vertex in renderer.sharedMesh.GetTriangles(s))visible.Add(vertex);for(int i=0;i<rest.Length;i++)if(visible.Contains(i)&&rest[i].y<.08f)')
text=text.replace('rows.Add(row);','rows.Add(row);yield return null;yield return null;')
text=text.replace('AudioListener.volume=0;', '''AudioListener.volume=0;
   foreach(var item in FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))if(item.GetType().Name=="DialogueHud"||item.GetType().Name=="CameraChatOverlay")item.enabled=false;''')
text=text.replace('camera.orthographic=true;camera.orthographicSize=size;', '''var originals=new List<SkinnedMeshRenderer>();var temporary=new List<GameObject>();var snapshots=new List<Mesh>();
   foreach(var r in FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))if(r.enabled){var mesh=new Mesh();r.BakeMesh(mesh);var go=new GameObject("Frozen current skinned mesh");go.transform.SetParent(r.transform,false);go.AddComponent<MeshFilter>().sharedMesh=mesh;go.AddComponent<MeshRenderer>().sharedMaterials=r.sharedMaterials;originals.Add(r);temporary.Add(go);snapshots.Add(mesh);r.enabled=false;}
   camera.orthographic=true;camera.orthographicSize=size;''')
text=text.replace('Destroy(image);rt.Release();Destroy(rt);','Destroy(image);rt.Release();Destroy(rt);foreach(var r in originals)r.enabled=true;foreach(var go in temporary){go.SetActive(false);Destroy(go);}foreach(var mesh in snapshots)Destroy(mesh);')
source=HERE/'ReviewSource-v2';source.mkdir(exist_ok=False)
for p in (HERE/'ReviewSource').rglob('*.cs'):
    write(source/p.relative_to(HERE/'ReviewSource'),text if p.name=='FootSourceReview.cs' else p.read_bytes())
managed=FINAL/'Player/MGFR_Data/Managed'
player=HERE/'ReviewPlayer-v2';player.mkdir(exist_ok=False)
module=player/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll';module.parent.mkdir(parents=True)
opts=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(module)]
opts+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!=module.name]
opts+=[str(p) for p in source.rglob('*.cs')]
rsp=HERE/'compile-v2.rsp';write(rsp,'\n'.join('"'+x+'"' for x in opts))
subprocess.run(['H:/MGFR/Editor/Data/NetCoreRuntime/dotnet.exe','H:/MGFR/Editor/Data/DotNetSdkRoslyn/csc.dll','@'+str(rsp)],check=True)
for p in (FINAL/'Player').rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(FINAL/'Player')
    if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
    target=player/rel;target.parent.mkdir(parents=True,exist_ok=True);os.link(p,target)
run=(HERE/'run_review.py').read_text(encoding='utf-8').replace("'ReviewPlayer/MGFR.exe'","'ReviewPlayer-v2/MGFR.exe'").replace("'Results'","'Results-v2'").replace("'player.log'","'player-v2.log'").replace("'startup.log'","'startup-v2.log'")
exec(compile(run,str(HERE/'run_review.py'),'exec'),{'__file__':str(HERE/'run_review.py'),'__name__':'__main__'})
