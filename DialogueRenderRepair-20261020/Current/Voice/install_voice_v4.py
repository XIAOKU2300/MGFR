"""Keep short lead-ins attached to natural clauses for stable speech/readback."""
from pathlib import Path
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
REVISION = 'structured-history-natural-clauses-v4'

def install(app, bridge_url):
    sys.path.insert(0, str(HERE))
    from install_voice_v3 import install as base_install
    base_install(app, bridge_url)
    from app.engines import tts_gptsovits
    original = tts_gptsovits.prepare_tts_text
    if not getattr(original, '_mgfr_natural_clauses', False):
        def natural_clauses(text):
            groups, pending = [], ''
            for phrase in original(text).splitlines():
                pending += phrase
                content = sum(unicodedata.category(char)[0] in 'LN' for char in pending)
                if content >= 8:
                    groups.append(pending)
                    pending = ''
            if pending:
                content = sum(unicodedata.category(char)[0] in 'LN' for char in pending)
                if groups and content < 4:
                    groups[-1] += pending
                else:
                    groups.append(pending)
            return '\n'.join(groups)
        natural_clauses._mgfr_natural_clauses = True
        tts_gptsovits.prepare_tts_text = natural_clauses
    import avatar_upgrade
    avatar_upgrade.REVISION = REVISION
    app.state.avatar_revision = REVISION
    app.state.conversation_repair = REVISION
