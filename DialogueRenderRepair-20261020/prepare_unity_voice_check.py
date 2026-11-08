from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'NativeMotionAdapt-20261020/test_voice_pipeline.py').read_text(encoding='utf-8')
source=source.replace("    import avatar_upgrade\n    avatar_upgrade.install(app)","    sys.path.insert(0,str(ROOT/'Current/Voice'))\n    import install_voice_v4\n    install_voice_v4.install(app,'http://127.0.0.1:1')")
source=source.replace("'network-'","'unity-voice-'")
with (HERE/'test_unity_voice.py').open('x',encoding='utf-8') as stream:stream.write(source)
print('Created actual player PCM/gesture integration check.')
