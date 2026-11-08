"""Create isolated, reviewed math-only C# probe. Never overwrites any file."""
from pathlib import Path
import struct, json, hashlib
ROOT = Path(__file__).resolve().parent
OUT = ROOT/'solver-probe-v1'
OUT.mkdir(exist_ok=False)
def put(name, content):
    with (OUT/name).open('x',encoding='utf-8') as f: f.write(content)
src=ROOT/'public-source'
native=Path('H:/Hypergryph Launcher/games/Arknights Endfield/UnityPlayer.dll')
data=native.read_bytes()
pe=struct.unpack_from('<I',data,60)[0]; sections=[]
count=struct.unpack_from('<H',data,pe+6)[0]; opt=struct.unpack_from('<H',data,pe+20)[0]
base=struct.unpack_from('<Q',data,pe+24+24)[0]
for i in range(count):
    pos=pe+24+opt+i*40
    vs,va,rs,rp=struct.unpack_from('<4I',data,pos+8)
    sections.append((va,max(vs,rs),rp))
def vaoffset(va):
    r=va-base
    for start,size,raw in sections:
        if start<=r<start+size: return raw+r-start
    raise ValueError(hex(va))
names=[]
for i in range(61):
    pos=vaoffset(struct.unpack_from('<Q',data,0x1c7dd40+i*8)[0])
    name=data[pos:data.index(b'\0',pos)].decode('ascii')
    if not name or len(name)>100: raise ValueError('unexpected name')
    names.append(name)
assert names[28]=='Left Foot Twist Roll' and names[-1]=='Right Hand In-Out'
put('native-muscles.json',json.dumps({'source_sha256':hashlib.sha256(data).hexdigest(),'pointer_table_raw_offset':hex(0x1c7dd40),'names':names},indent=2))
s=(src/'AvatarRigInput.cs').read_text(encoding='utf-8')
s='\n'.join(l for l in s.splitlines() if not l.startswith('using AssetRipper.'))
s=s[:s.index('    public static AvatarRigInput FromAvatar')]+s[s.index('    public static AvatarRigInput? FromDocumentJson'):]
s=s.replace('required ','').replace(': [];',': Array.Empty<AxesRow>();',1).replace(': [];',': Array.Empty<(Vector3, Quaternion)>();',1)
put('AvatarRigInput.cs',s)
s=(src/'AvatarMuscleReferential.cs').read_text(encoding='utf-8')
s=s.replace('using AssetRipper.SourceGenerated.Classes.ClassID_90;','')
s=s.replace('    public static AvatarMuscleReferential? TryCreate(IAvatar avatar) =>\n        TryCreate(AvatarRigInput.FromAvatar(avatar));','')
# New toe axes are hypotheses: excluded from the probe unless identically zero.
# Their presence and magnitude are reported by the Python export driver.
s=s.replace('for (FingerType finger = FingerType.Thumb; finger < FingerType.Last; finger++)','for (int finger = 0; finger < 5; finger++)')
s=s.replace('finger.ToAttributeString()', 'new[] { "Thumb", "Index", "Middle", "Ring", "Little" }[finger]')
put('AvatarMuscleReferential.cs',s)
for n in ['MuscleBone.cs','RootChannelPlan.cs']: put(n,(src/n).read_text(encoding='utf-8'))
s=(src/'BoneType.cs').read_text(encoding='utf-8').split('public static class BoneTypeExtensions')[0]
put('BoneType.cs',s)
put('Globals.cs','global using System;\nglobal using System.IO;\nglobal using System.Linq;\nglobal using System.Collections.Generic;\n')
put('Probe.runtimeconfig.json',json.dumps({'runtimeOptions':{'tfm':'net6.0','framework':{'name':'Microsoft.NETCore.App','version':'6.0.36'}}}))
refs=Path('C:/Program Files/dotnet/shared/Microsoft.NETCore.App/6.0.36')
rsp=['-nologo','-target:exe','-optimize+','-nullable:enable',f'-out:"{OUT}/Probe.dll"']
rsp += [f'-r:"{p}"' for p in refs.glob('*.dll') if not p.name.startswith(('api-ms-','clr','coreclr','mscord','msquic'))]
rsp += [f'"{p}"' for p in OUT.glob('*.cs')]+[f'"{ROOT}/ProbeMain.cs"']
put('compile.rsp','\n'.join(rsp))
print(OUT)
