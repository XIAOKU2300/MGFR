from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
base=root.parent/'HandCoexist-20261019/Project'
previous=root/'ShaderProject-v1'
project=root/'ShaderProject-xr-v2'
project.mkdir()
for name in ('Assets','ProjectSettings'):
    shutil.copytree(previous/name,project/name)
shutil.copytree(base/'Packages',project/'Packages')
(project/'Library/PackageManager').mkdir(parents=True)
shutil.copytree(base/'Library/PackageCache',project/'Library/PackageCache')
for path in (base/'Library/PackageManager').iterdir():
    content=path.read_text(encoding='utf-8-sig')
    content=content.replace(str(base).replace('\\','/'),str(project).replace('\\','/'))
    content=content.replace(str(base).replace('\\','\\\\'),str(project).replace('\\','\\\\'))
    content=content.replace(str(base),str(project))
    (project/'Library/PackageManager'/path.name).write_text(content,encoding='utf-8')
print(project)
