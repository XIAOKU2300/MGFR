from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'Project'
project=lab/'Project2'
assert not project.exists()
p=Path('Assets/MGFR/Scripts/Character/ControllerActions.cs')
s=(old/p).read_text(encoding='utf-8')
token='        public void Activate(int item)\n        {'
assert s.count(token)==1
s=s.replace(token,'''        void RefreshTargets()
        {
            if (Character == null) Character = FindAnyObjectByType<SiCharacterController>();
            if (floor == null) floor = FindAnyObjectByType<RoomFloorPlacement>();
            if (skins == null) skins = FindAnyObjectByType<SiSkinSwitcher>();
            if (voice == null) voice = FindAnyObjectByType<AutomaticVoiceSession>();
            if (captions == null) captions = FindAnyObjectByType<CameraChatOverlay>();
            if (idle == null) idle = FindAnyObjectByType<IdleMotionPlayer>();
            if (wardrobe == null) wardrobe = FindAnyObjectByType<WardrobeLiveRuntime>();
            if (hands == null) hands = FindAnyObjectByType<BareHandInteraction>();
        }
        public void Activate(int item)
        {
            RefreshTargets();''')
token='            if (View == null) return;'
assert s.count(token)==1
s=s.replace(token,'            RefreshTargets();\n'+token)
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old)==p]
for name in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/name,project/name,ignore=ignore)
with (project/p).open('x',encoding='utf-8',newline='\n') as output:output.write(s)
print(project)
