"""Download public repository metadata and text sources for read-only inspection."""
from pathlib import Path
import json
import urllib.request
import urllib.parse

root = Path(__file__).parent
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': 'http://127.0.0.1:7890'}))
base = 'https://api.github.com/repos/xinyang-sun/HandTrackingWithUnity-Mediapipe'

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'MGFR-source-research', 'Accept': 'application/vnd.github+json'})
    with opener.open(request, timeout=30) as response:
        return response.read()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as file:
        file.write(data)

branches_raw = fetch(base + '/branches?per_page=100')
save(root / 'branches.json', branches_raw)
branches = json.loads(branches_raw)
for branch in branches:
    name, commit = branch['name'], branch['commit']['sha']
    tree_raw = fetch(base + '/git/trees/' + commit + '?recursive=1')
    save(root / (urllib.parse.quote(name, safe='') + '-tree.json'), tree_raw)
    entries = json.loads(tree_raw)['tree']
    selected = [entry for entry in entries if entry['type'] == 'blob' and (
        entry['path'].endswith(('.py', '.cs', 'ProjectVersion.txt', 'manifest.json', 'requirements.txt'))
        or entry['path'].lower().endswith(('readme.md', 'license')))]
    print('BRANCH', name, commit, 'total entries', len(entries), 'selected text files', len(selected), flush=True)
    for entry in selected:
        path = entry['path']
        if entry.get('size', 0) > 300000:
            continue
        encoded = urllib.parse.quote(path, safe='/')
        raw_url = 'https://raw.githubusercontent.com/xinyang-sun/HandTrackingWithUnity-Mediapipe/' + commit + '/' + encoded
        data = fetch(raw_url)
        save(root / 'Sources' / urllib.parse.quote(name, safe='') / path, data)
        print(path, len(data), flush=True)
