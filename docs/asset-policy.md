# Asset policy — what is never committed

## Why

`祀.pmx` ships with a ReadMe that states, in its own words:

> 该模型为《明日方舟：终末地》IP的衍生作品，模型仅供个人展示与交流
> **请勿二次配布**，以及拆取部件以用于改造其他模型
> 请勿用于商业用途
> 最终解释权归属：鹰角网络

So: personal, non-commercial use only, and **no redistribution**. A public
repository containing the model, its textures, or any conversion of them would
be redistribution. The same logic applies to the 小酒狐 voice weights and to the
LLM API key.

This is not a "clean up later" item. Constraint #10 in
[`constraints.md`](constraints.md) requires these to be excluded **before the
first commit**.

## Never committed

| Class | Examples | Where it lives |
|---|---|---|
| Original model | `祀.pmx`, `ReadMe.txt` | `H:\MGFR\【明日方舟：终末地】祀_*/` |
| Model textures | `textures/`, `other tex/` (PNGs) | same folder |
| Converted assets | `.fbx`, `.blend`, exported meshes/materials | `converted/` (gitignored) |
| Voice weights | `小酒狐-e10.ckpt`, `小酒狐_e8_s184.pth` | `F:\TTS\_xiaojiuhu_check\` |
| Reference audio | `ref_xiaojiuhu.wav`, `idle50.wav` | `F:\` and `F:\TTS\` |
| Secrets | LLM API key, any `.env` | `dialogue-service/config.toml` (gitignored) |

Note that the model folder sits **inside the repository root**. It is excluded by
an explicit pattern (`【明日方舟：终末地】祀_*/`) plus blanket `*.pmx` / `*.pmd` /
`textures/` / `other tex/` rules, so it is safe to keep it where the user put it.

## Committed

- All source code in `dialogue-service/`, `unity-client/`, `tools/`
- Configuration **templates** (`config.example.toml`) — with empty secrets
- Documentation under `docs/`
- Synthetic test fixtures generated at test time, never recorded audio

## Enforcement

1. `.gitignore` blocks the paths above; `.gitattributes` marks the binary types.
2. `tools/check-no-ip-assets.ps1` fails if a forbidden path is ever staged. Run
   it before every commit, and wire it up as `.git/hooks/pre-commit`.
3. Review `git status --porcelain` output by hand on the first commit of any new
   asset directory. Do not commit on a green `git add -A` alone.

## What ships publicly

Code, import tooling and configuration examples only. A public release contains
no model, no conversion output, no voice weights and no keys; users supply their
own local copies.
