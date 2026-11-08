from pathlib import Path
import hashlib
import json
import shutil

lab = Path(__file__).resolve().parent
main = lab.parent / 'unity-client'
project = lab / 'Project1'
assert not project.exists()
changes = {}

def change(relative, old, new):
    path = Path(relative)
    text = changes.get(path, (main/path).read_text(encoding='utf-8-sig'))
    assert text.count(old) == 1, (relative, old[:100], text.count(old))
    changes[path] = text.replace(old, new)

loader = 'Assets/MGFR/Scripts/Character/SiCharacterLoader.cs'
change(loader, '        // ---- Mesh -----------------------------------------------------------', '''        public SiAppearance CaptureAppearance(string id, Mesh mesh = null, Material[] materials = null)
        {
            if (!IsReady) throw new InvalidOperationException("Character is not built.");
            return new SiAppearance { Id = id, DataRoot = ResolveDataRoot(dataFolder, dataRootOverride),
                Data = Data, Mesh = mesh != null ? mesh : Renderer.sharedMesh,
                Materials = (Material[])(materials ?? Materials).Clone() };
        }

        public void ApplyAppearance(SiAppearance appearance)
        {
            appearance.ValidateAgainst(Data);
            Data = appearance.Data; dataRootOverride = appearance.DataRoot;
            Materials = (Material[])appearance.Materials.Clone();
            Renderer.sharedMesh = appearance.Mesh; Renderer.sharedMaterials = Materials;
            LocalBounds = appearance.Mesh.bounds;
            Renderer.localBounds = LocalBounds;
            for (int i = 0; i < _boneTransforms.Length; i++)
            {
                var p = Data.bones[i].localScaled;
                _boneTransforms[i].localPosition = new Vector3(p[0], p[1], p[2]);
                _boneTransforms[i].localRotation = Quaternion.identity;
            }
            CacheMaterialMorphBase(Data);
            Status = "skin=" + appearance.Id + " vertices=" + Data.counts.vertices;
        }

        // ---- Mesh -----------------------------------------------------------''')

idle = 'Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs'
change(idle, '        void BindClient()', '''        public void RebindSkinRestPose(SiCharacterLoader loader)
        {
            // Preserve playback clock, speech state and the live pose. Calibrate
            // speaking axes in the target rest pose rather than an animated pose.
            var savedPositions = new Vector3[bones.Length];
            var savedRotations = new Quaternion[bones.Length];
            for (int i = 0; i < bones.Length; i++)
            {
                savedPositions[i] = bones[i].localPosition;
                savedRotations[i] = bones[i].localRotation;
                var p = loader.Data.bones[i].localScaled;
                rest[i] = new Vector3(p[0], p[1], p[2]);
                bones[i].localPosition = rest[i]; bones[i].localRotation = Quaternion.identity;
            }
            CalibrateSpeakingRest(loader.transform);
            for (int i = 0; i < bones.Length; i++)
            {
                bones[i].localPosition = savedPositions[i];
                bones[i].localRotation = savedRotations[i];
                lastPose[i] = savedRotations[i];
            }
        }
        void BindClient()''')

physics = 'Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs'
change(physics, '  public void ResetToAnimation()', '''  public void RebindSkinRestPose()
  {
   if(!IsReady)return;
   for(int i=0;i<rig.Length;i++)localRest[i]=V(Loader.Data.bones[i].localScaled);
   // Body-to-bone offsets and joint identities stay stable; changed ankle rest
   // coordinates propagate through the live bones to their kinematic targets.
   ResetToAnimation();
  }
  public void ResetToAnimation()''')

hands = 'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs'
change(hands, '  void Release(int h)', '''  public int SkinSurfaceTriangles=>surfaceQuery!=null?surfaceQuery.EligibleTriangles:0;
  public void PrepareSkinChange()
  {
   if(!IsReady)return;
   for(int h=0;h<2;h++)
   {
    Release(h);pinchState[h].Reset();Pinching[h]=false;blockedUntilOpen[h]=true;
    recoveryRemaining[h]=.12f;hasAcquire[h]=false;previousPalm[h]=Vector3.zero;
    for(int s=0;s<20;s++)SetColliderState(h,s,false);
   }
  }
  public void RebuildSkinSurface()
  {
   if(surfaceQuery!=null)surfaceQuery.Dispose();
   surfaceQuery=new HandSurfaceQuery(Physics);
  }
  void Release(int h)''')

style = 'Assets/MGFR/RenderStyles/ZmdEndfield/ZmdRenderStyle.cs'
change(style, 'public sealed class ZmdRenderStyle:MonoBehaviour', 'public sealed partial class ZmdRenderStyle:MonoBehaviour')
change(style, '   IsReady=true;SetActive(true);', '   IsReady=true;CacheOriginalAppearance();SetActive(true);')
change(style, 'Active=value;legacy.enabled=value?false:legacyEnabled;', 'Active=value;legacy.enabled=value||SkinSwitchingEnabled?false:legacyEnabled;')
change(style, '''   if(ZmdMaterials!=null)for(int i=0;i<ZmdMaterials.Length;i++)if(ZmdMaterials[i]!=PreviousMaterials[i])Destroy(ZmdMaterials[i]);
   foreach(var t in textures.Values)Destroy(t);if(zmdMesh!=null)Destroy(zmdMesh);if(studio!=null)Destroy(studio);''', '''   DisposeSkinVariants();
   foreach(var t in textures.Values)Destroy(t);if(studio!=null)Destroy(studio);''')

def ignore(directory, names):
    return [name for name in names if (Path(directory)/name).relative_to(main) in changes]

for folder in ['Assets', 'Packages', 'ProjectSettings']:
    shutil.copytree(main/folder, project/folder, ignore=ignore)
for path, source in changes.items():
    with (project/path).open('x', encoding='utf-8', newline='\n') as stream: stream.write(source)

module = project/'Assets/MGFR/Skins'
module.mkdir()
for source in (lab/'Source').glob('*.cs'):
    shutil.copyfile(source, module/source.name)

skin = lab.parent/'converted/skins/si-swimsuit-barefoot-ankle-v4'
skin_target = project/'Assets/StreamingAssets/skins'/skin.name
skin_target.mkdir(parents=True)
for name in ['si_model.json', 'si_model.bin', 'skin.json']:
    shutil.copyfile(skin/name, skin_target/name)
shutil.copytree(skin/'textures', skin_target/'textures')
with (skin_target/'.gitignore').open('x', encoding='ascii') as stream: stream.write('*\n!.gitignore\n')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest = {str(p): sha(p) for p in skin.rglob('*') if p.is_file()}
with (lab/'input-hashes.json').open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
with (lab/'main-baseline-hashes.json').open('x', encoding='utf-8') as stream:
    json.dump({str(main/p): sha(main/p) for p in changes}, stream, indent=2)
with (lab/'.gitignore').open('x', encoding='ascii') as stream: stream.write('/Project*/\n/Review*/\n*.log\n')
print('Prepared ' + str(project) + '; existing main files overwritten=0')
