---
name: efmi-mgfr-skin-porting
description: 将终末地 EFMI 皮肤转换为 MGFR 原生资源，或将已适配的 MGFR 皮肤接入 ZMD 渲染、运行时换肤、布料物理及手部触碰和捏拉。适用于 buf/ini/dds 转换、赤脚脚踝返修、材质适配和可交互皮肤交付；附带祀泳装的限定输入转换与布料接入工具。
---

# EFMI → MGFR 皮肤与游戏交互适配

按输入和用户要的交付物选路径。已有 `si_model.json`、`si_model.bin`、`textures/`、`skin.json` 时直接接入，不重复 EFMI 转换。能显示、会随骨骼动、能碰撞和能捏拉是不同能力，按用户要求实现，不能互相替代。

## 交付边界

- 用户只要转换资源时，交付独立资源；不自动改宿主、加换肤或部署。用户要求游戏内装载、物理或交互时，该要求包含相关接入工作。
- 源 Mod 和已适配模型保留原件。优先在新目录制作可运行版本；合入已有项目时遵守当前会话的覆盖/备份约定，已有明确授权不重复索要。
- 不把模型、贴图、原始缓冲、语音或凭据打进 skill 或公开提交。可以保留自写脚本、运行时代码模板和结构 profile；资源由调用者提供。
- 测试和说明按用户要求控制。默认编译加一次短启动/切换检查，简短交付启动入口；不自行扩展截图、长评测或头显验收。

## 选择路径

**已有 MGFR 皮肤，要渲染、装载和换肤：**读 [渲染与换肤接入](references/runtime-integration.md)。核对原生数据、材质语义和 rest/bind；建立皮肤独立材质及可恢复的运行时切换。

**已有皮肤，要裙片/袖片物理、触碰或捏拉：**继续读 [布料与手部交互](references/cloth-interaction.md)。先检查真实权重和可见布面；缺少动态骨骼权重时补独立布料求解，不能仅启动原 PMX 物理就宣称完成。相同祀 v4 输入可用 `scripts/prepare_interaction_candidate.py` 准备独立项目，工具会检查 profile 和宿主 API。

**同一套祀蓝白泳装 EFMI 原始输入：**读 [workflow.md](references/workflow.md)，先运行 `scripts/port_si.py inspect`，指纹匹配后再 `convert`。`--barefoot` 是限定案例的平脚候选，不是通用人体修改器。

**不同模型、骨架或导出版本：**读 [格式与映射](references/format-and-mapping.md)，重新检查实际 draw ranges、坐标、UV、材质和绑定。不要删掉旧 profile 的指纹保护来套新资源。

**赤脚、脚踝或小腿返修：**读 [ankle-review.md](references/ankle-review.md)。处理几何、静止骨架、bind pose 与 IK 目标；隐藏鞋子或重算法线不能修复轮廓。数值接地通过不等于用户认可自然度。

## 接入时保持的契约

- 骨骼名字/顺序/父子关系、形变名字和材质槽语义保持一致；赤脚皮肤可以有不同 rest 坐标，必须同时使用它的 inverse binds。
- 换肤同步动画 rest、物理目标、材质形变基值、抓取表面的索引结构，以及 GPU 蒙皮缓存。不要只替换贴图或只替换 sharedMesh。
- 材质换 Shader 后重新设置 renderQueue、混合、剔除和 ZWrite；新服装用自己的 D/N，未知 L 图不能直接当旧 P 图使用。
- 可见布面是交互目标。停用没有对应几何的旧衣物碰撞代理；布料抓取与旧骨骼抓取必须有明确的单手所有权。
- 默认只做最小必要检查。用户要求图或在处理局部视觉问题时再拍对应近景；需要独立渲染探针时读 [unity-verification.md](references/unity-verification.md)。

## 完成与交付

交付用户实际能启动的程序或其指定的资源目录，说明入口和必要按键。确认新资源被真正装载，布料求解和手部接入随该程序打包；旧启动入口不能证明新代码已生效。保留失败候选，明确哪些只是编译/短运行通过，未做的头显体验或视觉验收不能写成已通过。

原始转换/脚踝阶段的历史记录见 [case-status.md](references/case-status.md)；后续渲染、换肤和布料交付的准确范围见 [运行时案例状态](references/runtime-case.md)。需要较完整的资源交接记录时再读 [delivery-contract.md](references/delivery-contract.md)。
