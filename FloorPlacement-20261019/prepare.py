from pathlib import Path
import difflib, hashlib, json, shutil

lab=Path(__file__).resolve().parent
base=lab.parent/'Unified-20261019/Project2'
project=lab/'Project'
assert not project.exists()
changes={}
def once(source,a,b):
    assert source.count(a)==1,a[:80]
    return source.replace(a,b)
p=Path('Assets/MGFR/Scripts/Character/SiCharacterBootstrap.cs')
s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'        bool _originChecked;\n        bool _floorOrigin;\n        readonly List<XRInputSubsystem> _inputSubsystems = new List<XRInputSubsystem>(2);','        RoomFloorPlacement _floorPlacement;')
s=once(s,'            BuildDialogue();','''            BuildDialogue();
            _floorPlacement = gameObject.AddComponent<RoomFloorPlacement>();
            _floorPlacement.Bind(_cameraRig, _camera, _xrFollower, _controller);''')
start=s.index('                if (!_originChecked)')
end=s.index('\n            }\n            // Once handed to XR',start)
s=s[:start]+'''                if (_floorPlacement.Tick()) _xrMode = true;'''+s[end:]
start=s.index('            if (_xrMode || _xrFollower == null || !_xrFollower.HasTrackedPose) return;')
end=s.index('\n        }\n\n        void ApplyPreviewCamera()',start)
s=s[:start]+'''            if (_floorPlacement == null) return;
            _floorPlacement.EnterFromCurrentPose();
            _xrMode = _floorPlacement.RoomReady;'''+s[end:]
changes[p]=s
p=Path('Assets/MGFR/Scripts/Character/SiCharacterController.cs')
s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'''        {
            var forward = Vector3.ProjectOnPlane(viewerForward, Vector3.up);''','''        {
            PlaceOnGround(viewerPosition, viewerForward, distance, GroundHeight);
        }

        public void PlaceOnGround(Vector3 viewerPosition, Vector3 viewerForward, float distance, float groundHeight)
        {
            if (!float.IsFinite(viewerPosition.sqrMagnitude) || !float.IsFinite(viewerForward.sqrMagnitude) ||
                !float.IsFinite(groundHeight) || !float.IsFinite(distance)) return;
            var forward = Vector3.ProjectOnPlane(viewerForward, Vector3.up);''')
s=once(s,'''            defaultPosition = new Vector3(position.x, 0f, position.z);''','''            defaultPosition = new Vector3(position.x, 0f, position.z);
            defaultGroundHeight = groundHeight;
            defaultScale = CharacterScale;''')
changes[p]=s
p=Path('Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs')
s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'a=="-mgfr-unified-review"','a=="-mgfr-floor-review"||a=="-mgfr-unified-review"')
changes[p]=s

def ignore(directory,names):
    return [n for n in names if (Path(directory)/n).relative_to(base) in changes]
for name in ('Assets','Packages','ProjectSettings'):
    shutil.copytree(base/name,project/name,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as stream:stream.write(s)
for p in (lab/'Source').glob('*.cs'):
    target=project/'Assets/MGFR/Scripts/Character'/p.name
    assert not target.exists()
    shutil.copyfile(p,target)
patch=[]
for p,s in changes.items():
    before=(base/p).read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix())
with (lab/'floor-placement.patch').open('x',encoding='utf-8') as stream:stream.writelines(patch)
hashes={p.as_posix():hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes}
with (lab/'base-hashes.json').open('x',encoding='utf-8') as stream:json.dump(hashes,stream,indent=2)
with (lab/'desktop-no-runtime.json').open('x') as stream:stream.write('{}\n')
print(project)
