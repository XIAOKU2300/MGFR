from pathlib import Path
import json
root=Path(__file__).resolve().parent
project=root/'ProbeProject-v2'
if project.exists():raise SystemExit('Refuse existing project; preserve prior output')
(project/'Assets/Editor').mkdir(parents=True)
(project/'Packages').mkdir()
(project/'ProjectSettings').mkdir()
def new(path,data):
    with path.open('xb') as f:f.write(data)
base=Path(r'H:\MGFR\HandCoexist-20261019\Project')
for src,dest in [(base/'Assets/MGFR/Shaders/ChatOverlay.shader',project/'Assets/ChatOverlay.shader'),(base/'Assets/MGFR/Scripts/Dialogue/CameraChatOverlay.cs',project/'Assets/CameraChatOverlay.cs'),(root/'Runtime-v2/ChatOverlayChroma.shader',project/'Assets/ChatOverlayChroma.shader'),(root/'Runtime-v2/SubtitleChromaRepair.cs',project/'Assets/SubtitleChromaRepair.cs'),(base/'ProjectSettings/ProjectVersion.txt',project/'ProjectSettings/ProjectVersion.txt')]:new(dest,src.read_bytes())
probe=(root/'SubtitleProbe.cs').read_text(encoding='utf-8').replace('PixelProbe-v1','PixelProbe-v2')
new(project/'Assets/Editor/SubtitleProbe.cs',probe.encode('utf-8'))
new(project/'Packages/manifest.json',json.dumps({'dependencies':{'com.unity.modules.jsonserialize':'1.0.0','com.unity.modules.ui':'1.0.0','com.unity.modules.imgui':'1.0.0'}}).encode())
new(project/'Assets/ProbeStubs.cs',b'namespace MGFR.Character { public static class SiCharacterBootstrap { public const string SceneName="Probe"; } } namespace MGFR.Dialogue { public sealed class DialogueClient : UnityEngine.MonoBehaviour { public bool IsSpeaking; public string ServerState="listening", LastAsrText="", ReplyText=""; } }')
print(project)
