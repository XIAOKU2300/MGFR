from pathlib import Path
import json, shutil, sys
import numpy as np

lab=Path(__file__).resolve().parent
base=lab.parent/'ShoeLive-20261019/Project3'
project=lab/'Project'
assert not project.exists(), 'Use a new output directory'
changes={}
def edit(path, old, new):
    path=Path(path)
    s=changes.get(path,(base/path).read_text(encoding='utf8'))
    assert s.count(old)==1,(str(path),old[:70],s.count(old))
    changes[path]=s.replace(old,new)

runtime='Assets/MGFR/Wardrobe/WardrobeLiveRuntime.cs'
edit(runtime,'        public string Pending(int h)=>state[h].pending;',
     '        public string Pending(int h)=>state[h].pending;\n        public Vector3 HeldSocket(int h)=>Socket(state[h].held,state[h].anchor);')
edit(runtime,'public Vector3 startLocal,last;public float elapsed;',
     'public Vector3 startLocal,startSocketLocal,last;public float elapsed,pinchAge;')
edit(runtime,'{public GameObject go;public Vector3 grip;public int anchor;public int owner=-1;}',
     '{public GameObject go;public Vector3 grip;public Vector3[] grips;public int anchor;public int owner=-1;public bool canEquip;public float furthestSocket;}')
edit(runtime,'                hands.GrabStatus[h]="手持："+adapter.GetPart(s.held).label;',
'''                var heldPart=adapter.GetPart(s.held);
                if(IsShoe(heldPart)&&!p.canEquip)
                {
                    float distance=Vector3.Distance(point,Socket(s.held,p.anchor));
                    float heldScale=Mathf.Abs(skins.Loader.transform.lossyScale.x);
                    p.furthestSocket=Mathf.Max(p.furthestSocket,distance);
                    p.canEquip=distance>(heldPart.snapRadiusMetres+.02f)*heldScale||
                        p.furthestSocket>.045f*heldScale&&distance<p.furthestSocket-.025f*heldScale;
                }
                hands.GrabStatus[h]="手持："+adapter.GetPart(s.held).label;''')
edit(runtime,'                        Hold(h,id);DetachCount++;', '                        Hold(h,id,false);DetachCount++;')
edit(runtime,'        void Hold(int h,string id)', '        void Hold(int h,string id,bool allowEquip=true)')
edit(runtime,'            s.rotationOffset=Quaternion.Inverse(hands.Source.Frames[h].Joints[1].rotation)*p.go.transform.rotation;',
'''            p.canEquip=allowEquip;p.furthestSocket=0;
            s.rotationOffset=Quaternion.Inverse(hands.Source.Frames[h].Joints[1].rotation)*p.go.transform.rotation;''')
edit(runtime,'            if(mayEquip&&near&&facing&&adapter.TryEquip(id,out _))',
     '            if(mayEquip&&near&&facing&&(!IsShoe(part)||p.canEquip)&&adapter.TryEquip(id,out _))')
edit(runtime,'        public Vector3 DroppedGrip(string id)=>pieces[id].go.transform.TransformPoint(pieces[id].grip);',
'''        static bool IsShoe(WardrobePart part)=>part.id=="shoe_left"||part.id=="shoe_right";
        public Vector3 DroppedGrip(string id)=>pieces[id].go.transform.TransformPoint(pieces[id].grip);
        public Vector3 DroppedAnchor(string id,int anchor)=>pieces[id].go.transform.TransformPoint(pieces[id].grips[anchor]);''')
edit(runtime,'            if(s.blocked)return;',
'''            s.pinchAge=previouslyClosed?s.pinchAge+dt:0;
            if(s.blocked)return;''')
edit(runtime,'                Vector3 direction=new Vector3(part.pullDirectionLocal[0],part.pullDirectionLocal[1],part.pullDirectionLocal[2]);',
'''                bool shoe=IsShoe(part);
                // Measure shoe pull against the moving foot, so idle motion cannot detach it.
                if(shoe)delta-=root.InverseTransformPoint(Socket(part.id,s.anchor))-s.startSocketLocal;
                Vector3 direction=new Vector3(part.pullDirectionLocal[0],part.pullDirectionLocal[1],part.pullDirectionLocal[2]);''')
edit(runtime,'                if(Vector3.Dot(delta,direction)>=part.pullDistanceMetres&&s.elapsed>=.12f)',
'''                float pulled=shoe?delta.magnitude:Vector3.Dot(delta,direction);
                if(pulled>=part.pullDistanceMetres&&s.elapsed>=(shoe?.08f:.12f))''')
edit(runtime,'                        pieces.Add(id,new Piece{go=go,grip=vertices[part.anchors[s.anchor].vertex],anchor=s.anchor});',
'''                        var grips=new Vector3[part.anchors.Length];
                        for(int i=0;i<grips.Length;i++)grips[i]=vertices[part.anchors[i].vertex];
                        pieces.Add(id,new Piece{go=go,grip=grips[s.anchor],grips=grips,anchor=s.anchor});''')
edit(runtime,'''            // A held pinch never acquires again after a completed action.
            if(previouslyClosed||!pinches[h].CanAcquire)return;
            string pick=null;int pickAnchor=0;float best=.05f*.05f;
            foreach(var pair in pieces)
            {
                if(pair.Value.owner>=0)continue;
                float distance=(DroppedGrip(pair.Key)-point).sqrMagnitude;
                if(distance<best){best=distance;pick=pair.Key;}
            }
            if(pick!=null){Hold(h,pick);return;}''',
'''            // Shoes allow a short approach after closing; a long-held pinch never auto-grabs.
            if(!pinches[h].CanAcquire||previouslyClosed&&s.pinchAge>.25f)return;
            bool fresh=!previouslyClosed;
            string pick=null;int pickAnchor=0;float best=float.PositiveInfinity;
            float scale=Mathf.Abs(skins.Loader.transform.lossyScale.x);
            foreach(var pair in pieces)
            {
                if(pair.Value.owner>=0)continue;
                var part=adapter.GetPart(pair.Key);bool shoe=IsShoe(part);
                if(!shoe&&!fresh)continue;
                float reach=shoe?part.gripRadiusMetres*scale:.05f;
                for(int i=0;i<pair.Value.grips.Length;i++)
                {
                    float distance=(DroppedAnchor(pair.Key,i)-point).sqrMagnitude;
                    if(distance<best&&distance<reach*reach){best=distance;pick=pair.Key;pickAnchor=i;}
                }
            }
            if(pick!=null)
            {
                var p=pieces[pick];p.anchor=pickAnchor;p.grip=p.grips[pickAnchor];Hold(h,pick);return;
            }''')
edit(runtime,'''                if(!adapter.IsEquipped(part.id)||part.id==state[1-h].pending)continue;''',
'''                if(!adapter.IsEquipped(part.id)||part.id==state[1-h].pending||!fresh&&!IsShoe(part))continue;''')
edit(runtime,'''                    float reach=part.gripRadiusMetres*Mathf.Abs(skins.Loader.transform.lossyScale.x);''',
'''                    float reach=part.gripRadiusMetres*scale;
                    if(!IsShoe(part))reach=Mathf.Min(reach,.05f);''')
edit(runtime,'''            hands.CancelForWardrobe(h);
            var selected=adapter.GetPart(pick);''',
'''            s.startSocketLocal=skins.Loader.transform.InverseTransformPoint(Socket(pick,pickAnchor));
            hands.CancelForWardrobe(h);
            var selected=adapter.GetPart(pick);''')
edit(runtime,'            Status="捏住："+selected.label+"，沿衣物方向拉开";',
     '            Status="捏住："+selected.label+(IsShoe(selected)?"，向任意方向拉开即可脱鞋":"，沿衣物方向拉开");')
edit(runtime,'                Status="张手后，捏住扣点向外拉脱";',
     '                Status="鞋面或鞋跟附近捏合，拉开约 4.5 厘米脱鞋";')
edit(runtime,'            GUILayout.Label("张手 → 扣点捏合 → 拉脱；对准蓝点松手穿回");GUILayout.Label(Status);',
     '            GUILayout.Label("鞋面/鞋跟附近捏合 → 任意方向拉开；蓝点松手穿回");GUILayout.Label(Status);')

profile_path=Path('Assets/StreamingAssets/wardrobe/with_shoes/wardrobe.json')
profile=json.loads((base/profile_path).read_text(encoding='utf8'))
sys.path.insert(0,str(lab.parent/'tools/skins'))
from build_swimsuit_v1 import read_base
_,arrays,_=read_base(base/'Assets/StreamingAssets/skins/si-swimsuit-shoes')
positions,normals,_,bones,weights,*_=arrays
for part in profile['parts']:
    if not part['id'].startswith('shoe_'):continue
    ids=np.unique(np.fromfile(base/profile_path.parent/part['indexFile'],dtype='<u4'))
    p=positions[ids];side=1 if part['id']=='shoe_left' else -1
    chosen=[part['anchors'][0]['vertex']]
    for coord,sign in ((2,-1),(2,1),(1,1),(0,side)):
        vertex=int(ids[np.argmax(p[:,coord]*sign)])
        if vertex not in chosen:chosen.append(vertex)
    # Farthest-point samples cover toe, instep, heel and ankle straps.
    while len(chosen)<24:
        distances=np.min(np.linalg.norm(p[:,None]-positions[chosen],axis=2),axis=1)
        vertex=int(ids[np.argmax(distances)])
        assert vertex not in chosen
        chosen.append(vertex)
    coverage=float(np.min(np.linalg.norm(p[:,None]-positions[chosen],axis=2),axis=1).max())
    assert coverage<.055,(part['id'],coverage)
    part['anchors']=[dict(vertex=v,position=positions[v].tolist(),normal=normals[v].tolist(),
                           boneIndices=bones[v].astype(int).tolist(),boneWeights=weights[v].tolist()) for v in chosen]
    part.update(gripRadiusMetres=.08,pullDistanceMetres=.045,snapRadiusMetres=.10,snapAngleDegrees=65.)
    print(part['id'],'anchors',len(chosen),'max surface-to-anchor',round(coverage,4))
changes[profile_path]=json.dumps(profile,ensure_ascii=False,indent=2)

review='Assets/MGFR/Wardrobe/ShoeReview.cs'
edit(review,'            Move(live.DroppedGrip(id),false);for(int i=0;i<3;i++)Pump(last,false);',
     '            Move(live.DroppedAnchor(id,1),false);for(int i=0;i<3;i++)Pump(last,false);')
edit(review,'            Move(live.Socket(id),true);for(int i=0;i<3;i++)Pump(live.Socket(id),false);',
     '            Vector3 target=live.HeldSocket(0);Move(target,true);for(int i=0;i<3;i++)Pump(target,false);')
edit(review,'        void Detach(string id)\n',
     '        void Detach(string id,int anchor=0,Vector3? localPull=null,bool earlyPinch=false)\n')
edit(review,'''            Move(live.Socket(id),false);for(int i=0;i<3;i++)Pump(live.Socket(id),false);
            Vector3 socket=live.Socket(id);for(int i=0;i<3;i++)Pump(socket,true);''',
'''            var root=live.Hands.Physics.Loader.transform;
            bool shoe=id.StartsWith("shoe_");
            Vector3 offset=earlyPinch?root.TransformVector(Vector3.right*(id=="shoe_left"?.065f:-.065f)):Vector3.zero;
            Vector3 socket=live.Socket(id,anchor)+offset;
            if(earlyPinch)
            {
                Vector3 outside=live.Socket(id,anchor)+offset*2.5f;
                Move(outside,false);for(int i=0;i<3;i++)Pump(outside,false);
                for(int i=0;i<4;i++)Pump(outside,true);
                Check(live.Pending(0)==null,"shoe grabbed from too far away");
                Move(socket,true,6);
            }
            else {Move(socket,false);for(int i=0;i<3;i++)Pump(socket,false);}
            for(int i=0;i<3;i++)Pump(socket,true);''')
edit(review,'''            Vector3 direction=live.Hands.Physics.Loader.transform.TransformVector(new Vector3(d[0],d[1],d[2]));
            Move(socket+direction*part.pullDistanceMetres*1.5f,true,20);''',
'''            Vector3 direction=root.TransformVector(localPull??new Vector3(d[0],d[1],d[2]));
            for(int i=0;i<8;i++)Pump(socket,true);
            Check(live.IsEquipped(id),"stationary pinch detached "+id);
            Move(socket+direction*part.pullDistanceMetres*1.5f,true,12);''')
# Keep the short packaged check focused on input and state, without image rendering.
edit(review,'CheckFeet("both-on");Capture("01-both-on");','CheckFeet("both-on");')
edit(review,'int side=id=="shoe_left"?0:1;Detach(id);',
'''int side=id=="shoe_left"?0:1;
                Detach(id,side==0?4:2,side==0?Vector3.right:Vector3.up,side==0);''')
edit(review,'                if(side==0)Capture("02-one-off");Release();Reequip(id);',
'''                Release();Check(!live.IsEquipped(id),"freshly detached shoe snapped back on release");Reequip(id);''')
edit(review,'            Detach("shoe_left");Release();Detach("shoe_right");Release();',
'''            // Toe and upper strap work with different pull directions too.
            Detach("shoe_left",1,Vector3.forward);Release();
            Detach("shoe_right",3,Vector3.back);Release();''')
edit(review,'CheckFeet("both-off");Capture("03-both-off");report.Add("bothBarefootAndHeightRestored=PASS");',
     'CheckFeet("both-off");report.Add("bothBarefootAndHeightRestored=PASS");')
edit(review,'            report.Add("reset=PASS");report.Add("renderMorphs="+live.Hands.Physics.Loader.Renderer.sharedMesh.blendShapeCount);',
'''            report.Add("reset=PASS");
            // A pinch held for a long time cannot acquire by drifting near a shoe.
            Vector3 far=live.Socket("shoe_left",4)+live.Hands.Physics.Loader.transform.right*.3f;
            Move(far,false);for(int i=0;i<30;i++)Pump(far,true);
            Move(live.Socket("shoe_left",4),true);Check(live.Pending(0)==null,"long pinch auto-acquired");
            Release();for(int i=0;i<3;i++)Pump(last,true);
            Check(live.Pending(0)=="shoe_left","open/close did not rearm");
            live.Hands.Source.SetReplayFrame(0,Frame(last,true),false);live.Step(1f/60);
            Check(!live.OwnsHand(0)&&live.IsEquipped("shoe_left"),"tracking loss detached shoe");
            for(int i=0;i<6;i++)Pump(last,true);
            Check(live.Pending(0)==null,"tracking recovery acquired without opening");Release();
            report.Add("multiAnchor/arbitraryPull/65mmReach/earlyPinch/stationaryHold/longPinch/trackingLoss=PASS");
            report.Add("renderMorphs="+live.Hands.Physics.Loader.Renderer.sharedMesh.blendShapeCount);''')

def ignore(directory,names):
    return [n for n in names if (Path(directory)/n).relative_to(base) in changes]
for folder in ('Assets','ProjectSettings','Packages'):
    shutil.copytree(base/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf8') as f:f.write(s)
cache=base/'Library/PackageCache'
if cache.exists():shutil.copytree(cache,project/'Library/PackageCache')
with (lab/'流程记录.txt').open('x',encoding='utf8') as f:
    f.write('基于 ShoeLive Project3 制作独立易脱版本。\n每只鞋 24 个表面抓取点，范围 8cm，捏合后允许 0.25 秒内靠近抓取。\n任意方向拉开 4.5cm 脱鞋；扣除脚部自身运动。脱下后整只鞋可重新抓取。\n穿回范围 10cm、角度 65 度；保留跟踪丢失取消与张手复位。\n')
launcher=lab.parent/'启动MGFR鞋子易脱版.cmd'
with launcher.open('x',encoding='ascii',newline='') as f:
    f.write('@echo off\r\nsetlocal\r\nset "MGFR_EASY_ROOT=H:\\MGFR\\ShoeEasy-20261019"\r\n'
            'start "" "%MGFR_EASY_ROOT%\\Project\\Build\\Windows\\MGFR.exe" -mgfr-skins -mgfr-skin swimsuit -mgfr-zmd -mgfr-mr-clean-edge -mgfr-wardrobe -mgfr-shoes -logFile "%MGFR_EASY_ROOT%\\headset-%RANDOM%-%RANDOM%-%RANDOM%.log"\r\nendlocal\r\n')
print(project)
