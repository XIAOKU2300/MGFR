"""Assemble this repair into a new standalone package; never overwrite any source/package."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = ROOT / 'NativeMotionAdapt-20261020/Current'
OUT = HERE / 'Release-v1'
OUT.mkdir(exist_ok=False)
SOURCE = OUT / 'Source'
SOURCE.mkdir()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data.encode('utf-8') if isinstance(data, str) else data)

for path in (BASE / 'Source').glob('*.cs'):
    text = path.read_text(encoding='utf-8')
    if path.name == 'NativeAvatarActions-main.cs':
        text = text.replace('public static void Install(){var args=', 'public static void Install(){MGFR.Repairs.MrClothCoverageRepair.Install();var args=', 1)
        text = text.replace('var go=new GameObject("Native retargeted avatar actions");', 'if(Array.IndexOf(args,"-mgfr-render-repair-review")>=0)new GameObject("MR transparency acceptance").AddComponent<MGFR.Repairs.RenderRepairReview>();\n   var go=new GameObject("Native retargeted avatar actions");', 1)
    write(SOURCE / path.name, text)
text = (HERE / 'MrClothCoverageRepair.cs').read_text(encoding='utf-8')
text = text.replace('foreach(var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))foreach(var material in renderer.sharedMaterials){', '''foreach(var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None)){
    var materials=renderer.sharedMaterials;for(int index=0;index<materials.Length;index++){
    if(materials.Length==14&&(index<8||index>10))continue;
    if(materials.Length!=14&&renderer.name!="Simulated swimsuit cloth")continue;
    var material=materials[index];''')
text = text.replace('if(material==null||changed.Contains(material)||', 'if(material==null||')
text = text.replace('changed.Add(material);\n   }', 'changed.Add(material);\n   }}')
write(SOURCE / 'MrClothCoverageRepair.cs', text)
write(SOURCE / 'RenderRepairReview.cs', (HERE / 'RenderRepairReview.cs').read_bytes())
write(SOURCE / 'SubtitleChromaRepair.cs', (HERE / 'SubtitleCandidate/Runtime-v2/SubtitleChromaRepair.cs').read_bytes())
managed = BASE / 'Player/MGFR_Data/Managed'
work = OUT / 'Build'
work.mkdir()
plugin = work / 'MGFR.StructuredVoiceFinal.dll'
options = ['/nologo', '/target:library', '/nostdlib+', '/langversion:latest', '/out:' + str(plugin)]
options += ['/reference:' + str(path) for path in managed.glob('*.dll') if path.name != plugin.name]
options += [str(path) for path in SOURCE.glob('*.cs')]
response = work / 'compile.rsp'
write(response, '\n'.join('"'+x+'"' for x in options))
subprocess.run([str(ROOT / 'Editor/Data/NetCoreRuntime/dotnet.exe'), str(ROOT / 'Editor/Data/DotNetSdkRoslyn/csc.dll'), '@'+str(response)], check=True)
player = OUT / 'Player'
player.mkdir()
for path in (BASE / 'Player').rglob('*'):
    if not path.is_file():
        continue
    relative = path.relative_to(BASE / 'Player')
    if relative.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll', 'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:
        continue
    write(player / relative, path.read_bytes())
write(player / 'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll', plugin.read_bytes())
write(player / 'MGFR_Data/StreamingAssets/mgfr-mr-coverage', (HERE / 'ShaderBundle-v2/mgfr-mr-coverage').read_bytes())
voice = OUT / 'Voice'
voice.mkdir()
for name in ['avatar_json_v2.py', 'avatar_pipeline_v2.py', 'install_voice_v2.py']:
    text = (HERE / 'Voice' / name).read_text(encoding='utf-8')
    if name == 'install_voice_v2.py':
        text = text.replace('ROOT = HERE.parents[1]', "ROOT = next(p for p in HERE.parents if (p / 'SpeechNatural-20261019/VoiceService10').is_dir())")
    if name == 'avatar_pipeline_v2.py':
        text = text.replace('''                if not isinstance(item, EngineUnavailable):
                    raise item
                await session.emit_json(protocol.error(round_.id, ErrorCode.LLM_UNAVAILABLE, str(item)))''', '''                # Never expose provider response bodies; always close this round.
                logger.warning("structured_reply_failed kind=%s", type(item).__name__)
                await session.emit_json(protocol.error(round_.id, ErrorCode.LLM_UNAVAILABLE, "Reply unavailable; ready for next turn"))''')
    write(voice / name, text)
write(OUT / 'receipt.json', json.dumps({'sourceBase': str(BASE), 'player': str(player / 'MGFR.exe'), 'moduleSha256': hashlib.sha256(plugin.read_bytes()).hexdigest(), 'shaderBundle': 'ShaderBundle-v2'}, indent=2))
print('NEW_REPAIR_RELEASE', player / 'MGFR.exe')
