from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project1';project=lab/'Project2'
assert not project.exists()
changes={}
physics=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs')
s=(old/physics).read_text(encoding='utf-8')
old_block='''   // Body-to-bone offsets and joint identities stay stable; changed ankle rest
   // coordinates propagate through the live bones to their kinematic targets.
   ResetToAnimation();'''
new_block='''   // Keep proxy collisions only where the selected skin has weighted geometry.
   // A bikini must not leave invisible old skirt/sleeve grab targets in the room.
   var used=new bool[rig.Length];
   var pinned=new bool[rig.Length];
   for(int i=0;i<Bodies.Length;i++)if(Bodies[i].isKinematic)pinned[Data.bodies[i].bone]=true;
   void Mark(int bone,float weight)
   {
    if(weight<.01f)return;
    for(int p=bone;p>=0;p=Loader.Data.bones[p].parent){used[p]=true;if(pinned[p])break;}
   }
   foreach(var w in Loader.Renderer.sharedMesh.boneWeights)
   {Mark(w.boneIndex0,w.weight0);Mark(w.boneIndex1,w.weight1);Mark(w.boneIndex2,w.weight2);Mark(w.boneIndex3,w.weight3);}
   for(int i=0;i<Bodies.Length;i++)colliders[i].enabled=Data.bodies[i].group<4||used[Data.bodies[i].bone];
   ResetToAnimation();'''
assert s.count(old_block)==1
changes[physics]=s.replace(old_block,new_block)
hands=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs')
s=(old/hands).read_text(encoding='utf-8')
a='int id=grabbable[c];if(id==GrabbedBody[1-h])continue;'
assert s.count(a)==1
changes[hands]=s.replace(a,'int id=grabbable[c];if(id==GrabbedBody[1-h]||!garmentColliders[c].enabled)continue;')
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
 with (project/p).open('x',encoding='utf-8') as f:f.write(s)
shutil.copyfile(lab/'Source/SkinSwitchReview.cs',project/'Assets/MGFR/Skins/SkinSwitchReview.cs')
print(project)
