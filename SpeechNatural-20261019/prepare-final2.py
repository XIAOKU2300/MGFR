from pathlib import Path
lab=Path(__file__).resolve().parent
s=(lab/'prepare.py').read_text(encoding='utf-8')
s=s.replace('assert not service.exists()',"assert not (service/'app').exists()")
a='s=once(s,\'        pending = ""\\n\',\'\')'
b='s=s.replace(\'        pending = ""\\n\',\'\',1)'
assert s.count(a)==1
s=s.replace(a,b)
anchor='def once(s,a,b):'
addition='''changes[Path('app/text.py')]=changes[Path('app/text.py')].replace(r'(mm|cm|km|kg|ml|°c)\\b',r'(mm|cm|km|kg|ml|°c)(?![A-Za-z])').replace(r'(?<!\\d)\\.{2,}',r'\\.{2,}')
'''
assert s.count(anchor)==1
s=s.replace(anchor,addition+anchor)
exec(compile(s,str(lab/'prepare.py'),'exec'),{'__file__':str(lab/'prepare.py'),'__name__':'__main__'})
