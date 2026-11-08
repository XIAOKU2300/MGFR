from pathlib import Path
import hashlib
import json
import shutil

update=Path(__file__).resolve().parent
old=update/'Candidate/efmi-mgfr-skin-porting'
final=update/'Final/efmi-mgfr-skin-porting'
assert not final.exists()
relative=Path('references/cloth-interaction.md')
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old)==relative]
shutil.copytree(old,final,ignore=ignore)
source=(old/relative).read_text(encoding='utf-8')
anchor='先用 `prepare_interaction_candidate.py --inspect` 检查。'
assert source.count(anchor)==1
source=source.replace(anchor,anchor+'完整命令见 [准备工具与构建方式](runtime-tool.md)。')
with (final/relative).open('x',encoding='utf-8') as stream:stream.write(source)
plan=json.loads((update/'installation-plan.json').read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for record in plan['overwrites']:record['afterSha256']=sha(final/'SKILL.md')
for record in plan['newFiles']:
 path=final/Path(record['source']).relative_to(old)
 record['source']=str(path);record['sha256']=sha(path)
with (update/'installation-plan-final.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2)
print(final)
