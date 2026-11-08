"""Narrow ASR spelling correction for a verified local lore proper name."""


def install():
    from app.engines import tts_gptsovits
    from app.speech_verify import numbers
    original = tts_gptsovits.speech_completeness
    if getattr(original, '_mgfr_lore_readback', False):
        return

    def completeness(expected, recognized):
        # Observed SenseVoice readbacks of 墨魉: 墨量 / 墨两. Only normalize
        # this explicit name when it occurs in the expected sentence. Leave
        # speech text, numeric validation, other words and the .72 cutoff alone.
        if '墨魉' in expected and not numbers(expected):
            recognized = recognized.replace('墨量', '墨魉').replace('墨两', '墨魉')
        return original(expected, recognized)

    completeness._mgfr_lore_readback = True
    tts_gptsovits.speech_completeness = completeness
