from pathlib import Path

lab=Path(__file__).resolve().parent
code=(lab/'package_delivery.py').read_text(encoding='utf-8')
code=code.replace("(lab/receipt['review']).read_text()", "(lab/receipt['review']).read_text(encoding='utf-8')")
code=code.replace("(lab/receipt['interactionReview']).read_text()", "(lab/receipt['interactionReview']).read_text(encoding='utf-8')")
code=code.replace('assert not backup.exists();shutil.copyfile(main/rel,backup)',
 '''if backup.exists():assert sha(backup)==sha(main/rel)
        else:shutil.copyfile(main/rel,backup)''')
exec(compile(code,str(lab/'package_delivery.py'),'exec'),{'__file__':str(lab/'package_delivery.py')})
