from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent;old=lab/'Project';project=lab/'Project2';assert not project.exists()
changes={}
p=Path('Assets/MGFR/Scripts/Experience/LegPlantSolver.cs')
s=(old/p).read_text(encoding='utf8');assert s.count('bones[0].root.rotation')==1
changes[p]=s.replace('bones[0].root.rotation','bones[0].parent.rotation')
p=Path('Assets/MGFR/Wardrobe/ShoeReview.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('try{Run();Finish(true,"");}', '''try{
                var controller=FindAnyObjectByType<MGFR.Character.SiCharacterController>();if(controller!=null)controller.enabled=false;
                live.Hands.Physics.Loader.transform.rotation=Quaternion.Euler(0,33,0);
                Run();Finish(true,"");}''')
s=s.replace('            cam.Render();var old=RenderTexture.active;', '''            var renderer=loader.Renderer;var snapshot=new Mesh();renderer.BakeMesh(snapshot);
            var display=new GameObject("current baked shoe pose");display.transform.SetParent(renderer.transform,false);
            display.AddComponent<MeshFilter>().sharedMesh=snapshot;display.AddComponent<MeshRenderer>().sharedMaterials=renderer.sharedMaterials;
            renderer.enabled=false;cam.Render();renderer.enabled=true;Destroy(display);Destroy(snapshot);
            var old=RenderTexture.active;''')
s=s.replace('Check(foot.Weights[side]<.001f&&foot.Weights[1-side]>.999f,"foot poses not independent");',
    'Check(foot.Weights[side]<.001f&&foot.Weights[1-side]>.999f,"foot poses not independent");\n                CheckFeet("single-"+id);')
s=s.replace('Check(live.Adapter.Profile.parts.Length==10,"not ten parts");Capture', 'Check(live.Adapter.Profile.parts.Length==10,"not ten parts");CheckFeet("both-on");Capture')
s=s.replace('            Capture("03-both-off");','            CheckFeet("both-off");Capture("03-both-off");')
needle='        void Run()'
extra='''        void CheckFeet(string label)
        {
            var renderer=live.Hands.Physics.Loader.Renderer;var mesh=new Mesh();renderer.BakeMesh(mesh);
            var posed=mesh.vertices;var rest=renderer.sharedMesh.vertices;int[] body=renderer.sharedMesh.GetTriangles(7);
            for(int side=0;side<2;side++)
            {
                string id=side==0?"shoe_left":"shoe_right";float min=float.PositiveInfinity;
                if(live.IsEquipped(id))
                {
                    byte[] bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"wardrobe/with_shoes",live.Adapter.GetPart(id).indexFile));
                    int[] ids=new int[bytes.Length/4];Buffer.BlockCopy(bytes,0,ids,0,bytes.Length);
                    foreach(int vertex in ids)min=Mathf.Min(min,posed[vertex].y);
                }
                else foreach(int vertex in body)
                    if(rest[vertex].y<.055f&&rest[vertex].x*(side==0?1:-1)>0)min=Mathf.Min(min,posed[vertex].y);
                report.Add(label+" "+id+" soleY="+min);
                Check(min>-.015f&&min<.025f,"foot ground gap: "+label+" "+id+" "+min);
                Check(Quaternion.Angle(renderer.bones[side==0?23:27].rotation,renderer.transform.rotation)<.01f,"foot yaw does not follow placement");
            }
            Destroy(mesh);
        }
'''
assert s.count(needle)==1;s=s.replace(needle,extra+needle);changes[p]=s
def ignore(directory,names):return[n for n in names if (Path(directory)/n).relative_to(old) in changes]
for folder in ('Assets','ProjectSettings','Packages'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf8') as f:f.write(s)
cache=old/'Library/PackageCache'
if cache.exists():shutil.copytree(cache,project/'Library/PackageCache')
print(project)
