from pathlib import Path
import json,urllib.request
lab=Path('H:/MGFR/HandLab-20261018')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7890'}))
with opener.open('https://packages.unity.com/com.unity.xr.hands',timeout=25) as response:data=response.read()
with (lab/'registry-hands.json').open('xb') as f:f.write(data)
registry=json.loads(data);print('tags',registry.get('dist-tags'))
versions=[v for v in registry['versions'] if '-' not in v]
for version in sorted(versions,key=lambda v:tuple(int(x) for x in v.split('.')))[-6:]:
 item=registry['versions'][version]
 print(version,'unity',item.get('unity'), 'dependencies',item.get('dependencies'), 'tarball',item['dist']['tarball'])
