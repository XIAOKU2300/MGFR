# Tools

Local-only helpers. Nothing here ships to the headset and nothing here is part of
the running service — these are the scripts that keep the repository honest and
the model conversion reproducible.

| File | Purpose |
|---|---|
| `check-no-ip-assets.ps1` | Pre-commit guard: fails if a character asset, voice weight or secret is staged. |
| `model-conversion.md` | The offline PMX → binary procedure, including the morph and texture checks that must not be skipped. |
| `pmx/` | The converter itself: `pmx_reader.py` (format), `inspect_pmx.py` (dump), `convert_si.py` (convert). |
| `run-player.ps1` | Launches the desktop player after checking the player binary, the service and GPT-SoVITS, and reports what it found. |

## `check-no-ip-assets.ps1`

The 祀 model ReadMe forbids redistribution (二次配布), and the 小酒狐 voice weights
and the LLM key are private. `docs/asset-policy.md` states the rule; this script is
what makes it enforceable.

It inspects the **git index** (`git ls-files`) rather than the working tree, because
the index is what a commit would actually contain. A file sitting untracked on disk
is expected and is reported, not failed on.

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\check-no-ip-assets.ps1
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Clean. |
| `1` | Violations staged — do not commit. |
| `2` | Git is not available, so nothing could be checked. |

Exit code `2` is deliberately distinct from `1`: "I could not check" is not the
same answer as "I checked and it is fine", and a guard that silently passes when
its tool is missing is worse than no guard.

Run it before every commit until it is wired into a hook. It is not installed as a
hook automatically, because this repository does not yet assume git is present.
