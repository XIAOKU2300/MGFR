"""Offline recovery cases plus actual Unity PCM/body playback on the delivered package."""
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
for name in ['Voice/test_delivered_recovery.py','test_voice_final_player.py']:
    subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/name)],check=True)
print('Delivered dialogue recovery and Unity audio/body integration passed.')
