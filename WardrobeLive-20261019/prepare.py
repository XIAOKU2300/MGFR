from pathlib import Path
import shutil,hashlib,json

lab=Path(__file__).resolve().parent
base=lab.parent/'MrEdge-20261019/Project'
project=lab/'Project'
assert not project.exists()
changes={}
def edit(relative,old,new):
    p=Path(relative)
    s=changes.get(p,(base/p).read_text(encoding='utf8'))
    assert s.count(old)==1,(relative,old[:90],s.count(old))
    changes[p]=s.replace(old,new)

cloth='Assets/MGFR/Skins/ClothPhysics/SwimsuitClothRuntime.cs'
edit(cloth,'using MGFR.BareHands;','using MGFR.BareHands;\nusing MGFR.Wardrobe;')
edit(cloth,'        bool OwnsHand(int hand)=>Active&&Solver!=null&&Solver.Grips[hand].particle>=0;',
    '        bool OwnsHand(int hand)=>(WardrobeLiveRuntime.Instance!=null&&WardrobeLiveRuntime.Instance.OwnsHand(hand))||(Active&&Solver!=null&&Solver.Grips[hand].particle>=0);')
edit(cloth,'            sourceIds=ids.ToArray();','            wardrobeMap=map;wardrobeTriangles=(int[])triangles.Clone();\n            sourceIds=ids.ToArray();')
edit(cloth,'        void LateUpdate()\n        {','        public bool Manual;\n        void LateUpdate(){if(!Manual)Tick(Time.deltaTime);}\n        public void Tick(float delta)\n        {')
edit(cloth,'            UpdateGrabs(Time.deltaTime);BuildContacts();','            UpdateGrabs(delta);BuildContacts();')
edit(cloth,'                Solver.Step(Time.deltaTime,body,handCapsules,wind);','                Solver.Step(delta,body,handCapsules,wind);')
edit(cloth,'                var frame=hands.Source.Frames[h];bool tracked=hands.PreferBareHands&&frame.Tracked;',
    '                if(WardrobeLiveRuntime.Instance!=null&&WardrobeLiveRuntime.Instance.OwnsHand(h)){pinch[h].Reset();blocked[h]=true;continue;}\n                var frame=hands.Source.Frames[h];bool tracked=hands.PreferBareHands&&frame.Tracked;')
extensions='''        Dictionary<int,int> wardrobeMap;
        int[] wardrobeTriangles;
        public Mesh FullRenderMesh
        {
            get {var current=skins.Loader.Renderer.sharedMesh;return fullMeshes.TryGetValue(current,out var full)?full:current;}
        }
        public int VisibleClothTriangles=>visual!=null?visual.triangles.Length/3:0;
        public void SetWardrobeMesh(Mesh full)
        {
            if(!stripped.TryGetValue(full,out var without))
            {
                without=Instantiate(full);without.name=full.name+" wardrobe + separate XPBD";
                stripped.Add(full,without);fullMeshes.Add(without,full);
            }
            for(int s=0;s<full.subMeshCount;s++)without.SetTriangles(s==10?Array.Empty<int>():full.GetTriangles(s),s,false);
            skins.Loader.ReplaceSkinMesh(without);
        }
        public void ReleaseWardrobeMesh(Mesh full)
        {
            if(!stripped.TryGetValue(full,out var without))return;
            if(skins!=null&&skins.Loader!=null&&skins.Loader.Renderer!=null&&skins.Loader.Renderer.sharedMesh==without)
            {
                // Find the current style's unmodified complete source, not the adapter clone.
                skins.Style.SetActive(skins.Style.Active);
            }
            stripped.Remove(full);fullMeshes.Remove(without);Destroy(without);
        }
        static int WardrobeGroup(string id)=>id=="sleeve_left"?0:id=="sleeve_right"?1:id=="chest_frill"?2:id=="cover_skirt"?3:-1;
        public bool TryWardrobeVertex(int source,out Vector3 world)
        {
            world=Vector3.zero;
            if(vertices==null||wardrobeMap==null||!wardrobeMap.TryGetValue(source,out var index))return false;
            world=skins.Loader.transform.TransformPoint(vertices[index]);return true;
        }
        void SetWardrobeGroup(int group,bool shown)
        {
            Solver.EnabledGroups[group]=shown;Solver.ResetGroup(group);
            var t=new List<int>(wardrobeTriangles.Length);
            for(int i=0;i<wardrobeTriangles.Length;i+=3)
                if(Solver.EnabledGroups[Solver.RenderGroupForVertex(wardrobeTriangles[i])])
                {t.Add(wardrobeTriangles[i]);t.Add(wardrobeTriangles[i+1]);t.Add(wardrobeTriangles[i+2]);}
            visual.SetTriangles(t,0,false);
        }
        public bool SuspendWardrobePart(string id,out Vector3[] all)
        {
            all=null;int group=WardrobeGroup(id);if(group<0||Solver==null||!Active)return false;
            var baked=new Mesh();skins.Loader.Renderer.BakeMesh(baked);all=baked.vertices;Destroy(baked);
            for(int i=0;i<sourceIds.Length;i++)all[sourceIds[i]]=vertices[i];
            SetWardrobeGroup(group,false);return true;
        }
        public void ResumeWardrobePart(string id)
        {int group=WardrobeGroup(id);if(group>=0&&Solver!=null)SetWardrobeGroup(group,true);}
'''
edit(cloth,'        void UpdateDrivers()',extensions+'        void UpdateDrivers()')

solver='Assets/MGFR/Skins/ClothPhysics/SwimsuitClothSolver.cs'
edit(solver,'        public Particle[] Particles;','''        public readonly bool[] EnabledGroups={true,true,true,true};
        public int RenderGroupForVertex(int index)=>renderGroup[index];
        public void ResetGroup(int group)
        {
            for(int h=0;h<2;h++)if(Grips[h].particle>=0&&Particles[Grips[h].particle].group==group)Release(h);
            for(int i=0;i<Particles.Length;i++)if(Particles[i].group==group)
            {var p=Particles[i];p.position=p.previous=p.target;Particles[i]=p;}
        }
        public Particle[] Particles;''')
edit(solver,'                if(Particles[i].inverseMass<.12f||Grips[1-hand].particle==i)continue;',
    '                if(!EnabledGroups[Particles[i].group]||Particles[i].inverseMass<.12f||Grips[1-hand].particle==i)continue;')
edit(solver,'                    if(p.inverseMass==0){p.position=p.previous=p.target;Particles[i]=p;continue;}',
    '                    if(!EnabledGroups[p.group]||p.inverseMass==0){p.position=p.previous=p.target;Particles[i]=p;continue;}')
edit(solver,'                        var link=links[i];ref var a=ref Particles[link.a];ref var b=ref Particles[link.b];',
    '                        var link=links[i];if(!EnabledGroups[Particles[link.a].group])continue;ref var a=ref Particles[link.a];ref var b=ref Particles[link.b];')
edit(solver,'                        var p=Particles[i];if(p.inverseMass==0)continue;',
    '                        var p=Particles[i];if(!EnabledGroups[p.group]||p.inverseMass==0)continue;')

hands='Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs'
edit(hands,'  void Release(int h)','  public void CancelForWardrobe(int h){Release(h);blockedUntilOpen[h]=true;acquisitionPending[h]=false;}\n  void Release(int h)')
skins='Assets/MGFR/Skins/SiSkinSwitcher.cs'
edit(skins,'        public int SwitchCount { get; private set; }','        public event Action BeforeAppearanceChange;\n        public int SwitchCount { get; private set; }')
edit(skins,'            hands.PrepareSkinChange();','            BeforeAppearanceChange?.Invoke();\n            hands.PrepareSkinChange();')
voice='Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs'
edit(voice,'a=>a=="-mgfr-cloth-motion-review"','a=>a=="-mgfr-wardrobe-review"||a=="-mgfr-cloth-motion-review"')

def ignore(directory,names):
    return [n for n in names if (Path(directory)/n).relative_to(base) in changes]
for folder in ('Assets','ProjectSettings','Packages'):shutil.copytree(base/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf8') as f:f.write(s)

adapter=(lab.parent/'WardrobeAdapt-20261019/Package/Adapter/WardrobeAdapter.cs').read_text(encoding='utf8')
adapter=adapter.replace('        bool disposed;','        bool externalOwner;\n        public Mesh VisibleMesh=>working;\n        bool disposed;')
adapter=adapter.replace('WardrobeAdapter(SkinnedMeshRenderer target, string profileDirectory)', 'WardrobeAdapter(SkinnedMeshRenderer target, string profileDirectory, Mesh fullSourceMesh=null)')
adapter=adapter.replace('renderer = target; original = target.sharedMesh;','renderer = target; original = fullSourceMesh!=null?fullSourceMesh:target.sharedMesh;externalOwner=fullSourceMesh!=null;')
adapter=adapter.replace('            renderer.sharedMesh=working;', '            if(!externalOwner)renderer.sharedMesh=working;')
adapter=adapter.replace('if(renderer.sharedMesh!=working)throw', 'if(!externalOwner&&renderer.sharedMesh!=working)throw')
adapter=adapter.replace('if(renderer!=null&&renderer.sharedMesh==working)renderer.sharedMesh=original;', 'if(!externalOwner&&renderer!=null&&renderer.sharedMesh==working)renderer.sharedMesh=original;')
adapter=adapter.replace('                go=new GameObject(part.label+" detached");', '                baked.RecalculateNormals();baked.RecalculateTangents();\n                go=new GameObject(part.label+" detached");')
runtime=(lab/'Source/WardrobeLiveRuntime.cs').read_text(encoding='utf8')
runtime=runtime.replace('            bool closed=pinches[h].Update(f,dt);','''            if(s.held!=null)
            {
                var heldPiece=pieces[s.held];heldPiece.go.transform.rotation=f.Joints[1].rotation*s.rotationOffset;
                heldPiece.go.transform.position+=point-heldPiece.go.transform.TransformPoint(heldPiece.grip);
            }
            bool previouslyClosed=pinches[h].Closed;
            bool closed=pinches[h].Update(f,dt);''')
runtime=runtime.replace('            if(!pinches[h].CanAcquire)return;', '            if(previouslyClosed||!pinches[h].CanAcquire)return;')
runtime=runtime.replace('            if(hands.GrabbedBody[h]>=0)return;','')
runtime=runtime.replace('            cloth.ReleaseWardrobeMesh(mesh);','            if(cloth!=null)cloth.ReleaseWardrobeMesh(mesh);')
runtime=runtime.replace('        public void ResumePart(string id)=>cloth.ResumeWardrobePart(id);','        public void ResumePart(string id){if(cloth!=null)cloth.ResumeWardrobePart(id);}')

for name,s in [('WardrobeAdapter.cs',adapter),('WardrobeLiveRuntime.cs',runtime)]:
    p=project/'Assets/MGFR/Wardrobe'/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:f.write(s)
    p=lab/'Candidate'/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:f.write(s)
for name in ('barefoot_v4',):
    src=lab.parent/'WardrobeAdapt-20261019/Package'/name
    dest=project/'Assets/StreamingAssets/wardrobe'/name
    shutil.copytree(src,dest,ignore=shutil.ignore_patterns('model'))
cache=base/'Library/PackageCache'
if cache.is_dir():shutil.copytree(cache,project/'Library/PackageCache')
receipt={'base':str(base),'existingFilesOverwritten':0,'changedInNewProject':[str(p) for p in changes],
    'sourceHashes':{str(base/p):hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes}}
with (lab/'prepare-receipt.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
print(project)
