from pathlib import Path
import json
import urllib.request
import urllib.parse

root = Path(__file__).parent
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': 'http://127.0.0.1:7890'}))
repo = 'xinyang-sun/HandTrackingWithUnity-Mediapipe'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'MGFR-source-research'})
    with opener.open(req, timeout=25) as response: return response.read()

def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as file: file.write(data)

branches = json.loads((root/'branches.json').read_text())
for branch in branches:
    name, sha = branch['name'], branch['commit']['sha']
    if name not in ('Python', 'Unity'): continue
    path = root/(name+'-tree.json')
    if not path.exists(): write_new(path, fetch(f'https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1'))
    tree = json.loads(path.read_text())['tree']
    for entry in tree:
        if entry['type'] != 'blob': continue
        relative = entry['path']
        if name == 'Python': selected = '/' not in relative and relative.endswith(('.py','.md'))
        else: selected = relative.endswith(('.cs','ProjectVersion.txt','manifest.json')) and not relative.startswith(('Library/','Packages/'))
        if not selected: continue
        print(name, relative, entry.get('size',0), flush=True)
        if name == 'Unity' and relative.endswith('.cs'): continue
        target = root/'Sources'/name/relative
        if not target.exists():
            url = f'https://raw.githubusercontent.com/{repo}/{sha}/'+urllib.parse.quote(relative, safe='/')
            write_new(target, fetch(url))
