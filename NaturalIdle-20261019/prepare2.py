from pathlib import Path

lab=Path(__file__).resolve().parent
source=lab/'Source2'
source.mkdir()
for original in (lab/'Source').glob('*.cs'):
    text=original.read_text(encoding='utf-8')
    if original.name=='NaturalIdlePose.cs':
        # Longest phrase ends before the next slot, including its quiet tail.
        text=text.replace('seconds/23f','seconds/29f').replace('slot*23+2','slot*29+2')
    with (source/original.name).open('x',encoding='utf-8') as f:f.write(text)
code=(lab/'prepare.py').read_text(encoding='utf-8')
code=code.replace("project = lab / 'Project1'", "project = lab / 'Project2'")
code=code.replace("lab/'Source'", "lab/'Source2'")
code=code.replace("lab/'changes.patch'", "lab/'changes2.patch'")
code=code.replace("lab/'baseline-hashes.json'", "lab/'baseline-hashes2.json'")
code=code.replace("with (lab/'desktop-no-runtime.json').open('x',encoding='ascii') as f:f.write('{}\\n')", '')
exec(compile(code,str(lab/'prepare.py'),'exec'),{'__file__':str(lab/'prepare.py')})
