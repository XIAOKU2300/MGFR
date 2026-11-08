from pathlib import Path
import urllib.request
import urllib.parse

root = Path(__file__).parent
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7890'}))
sha = '6c9a9a2cbecc5bd70f29b45e710cd5cbf2bbd42d'
files = ['Assets/HandTracking.cs','Assets/DepthCalibrator.cs','Assets/PickUp.cs','Assets/TransformLink.cs','Assets/UDPReceive.cs','Assets/ChangeCamera.cs','Packages/manifest.json']
for relative in files:
    url = f'https://raw.githubusercontent.com/xinyang-sun/HandTrackingWithUnity-Mediapipe/{sha}/'+urllib.parse.quote(relative,safe='/')
    request = urllib.request.Request(url,headers={'User-Agent':'MGFR-source-research'})
    with opener.open(request,timeout=25) as response: data=response.read()
    target=root/'Sources/Unity'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as file: file.write(data)
    print(relative,len(data),flush=True)
