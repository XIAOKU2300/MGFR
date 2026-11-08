# 双眼衣物与退出修复

修复已直接启用到原启动入口实际加载的 `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\Player\MGFR.exe`。日常继续使用 `H:\MGFR\启动MGFR.cmd`。

## 修复内容

- **右眼没有衣服**：上一版独立材质构建没有 XR 加载器，构建流程裁掉了 `STEREO_INSTANCING_ON` 版本。相同 D3D11 双眼绘制中，旧包六种衣物／字幕材质均为左眼 27,556 像素、右眼 0。新包保留普通与原生双眼版本，覆盖衣物、字幕和当前手势面板共八种材质。
- **程序突然退出**：用户对应日志在 16:36:36 记录 XR 会话进入 EXITING，随后进入 `OpenXRRestarter.Shutdown`。没有找到原生崩溃转储或异常终止证据。现通过 OpenXR 的公开 `wantsToQuit` 事件拦截由 XR 会话结束触发的应用退出，保留窗口和现有对话，等待 SDK 清理后最多尝试三次恢复本程序的 XR 加载器。普通窗口关闭及应用主动退出仍正常接受。
- **诊断**：主启动器增加独立进程退出记录；XR 事件、焦点变化、错误数量和心跳另存为 session 日志。不会把对话、密钥或原始异常消息写入新增诊断记录。
- 保留用户选择的薄纱网点透视、衣物等比缩放、当前全部动作、手势面板和原语音配置。没有替换模型或音色。

## 已完成验证

| 检查 | 结果与证据 |
|---|---|
| 旧包复现 | `Probe-old-package/result.json`：六种材质全部右眼 0 像素，左眼正常 |
| 最终材质编译 | `Bundle-final/variant-audit.txt`：24 个通道／阶段均同时保留普通与双眼版本，没有残留构建标记 |
| 实际播放器的 GPU 双眼输出 | `Review-stability-20261020-211429-082964/Stereo/result.json`：八种材质 × 两种透明度 × 普通／绿幕模式，共 32 组；两眼均有画面，相同相机矩阵下像素差异均为 0 |
| 100 秒持续运行 | 同目录 `result.json`：5,935 帧、25 次动作、8 次换装、9 次缩放、三次 SDK 退出请求均被拦截；异常数及非有限衣物粒子数为 0；动作资源读取数保持 166 |
| 普通视图及透明材质 | `Review-render-20261020-211314-474254/Results/result.json`：两套服装、两种风格通过；普通视图与原材质最大像素误差 0 |
| 已启用主程序：缩放 | `Review-scale-20261020-211806-193063/result.json`：0.2、0.5、1、2、4 倍及恢复，布面和脱下鞋子的比例检查通过 |
| 已启用主程序：待机／对话／LLM 动作队列 | `Review-native-20261020-211936-364102/Results/result.json`：58 根骨骼，五阶段异常突跳 0；收尾、打断、回待机和换肤连续性通过 |
| 已启用主程序：手势与退出监控 | `Review-menu-monitored-20261020-212140-346632/Results/result.json`：全部面板检查通过；`player-exit.json` 记录正常退出 0 |
| 异常退出记录 | `Monitor-check/`：分别检查子进程返回 0 和 7，分类及退出码均正确 |

这些是桌面播放器、实际显卡双眼纹理和合成输入测试。没有实戴 Pico 检查，也没有验证真实断连后的头显重连；不能据此声称头显端已全面验收。实际串流边缘仍遵循用户接受的薄纱方案。100 秒测试中最高单帧约 210ms，因此该检查证明此测试过程没有异常退出，不代表头显帧时间保证。

## 入口和源码

- 日常启动：`H:\MGFR\启动MGFR.cmd`。
- 可重复测试：`H:\MGFR\测试入口\08-双眼与稳定性.cmd`。检查当前主程序的 32 组双眼输出和 100 秒持续运行，不使用话筒或远程 LLM。
- 当前运行时代码：`H:\MGFR\DialogueRenderRepair-20261020\Final-v3\Source`。现有手势面板和新增动作代码已保留。
- 正确的材质构建源：本目录 `ShaderProject-retained`，构建方法 `StereoRetainedBundle.Run`。构建前用专门标记保留两个独立版本，在编译回调中将标记还原为 Unity 原生双眼关键字，运行时无需自定义双眼开关。
- 重新构建时传入新的 `-mgfr-shader-output` 绝对目录；已存在的输出目录会被拒绝覆盖。构建同时检查普通与双眼版本，不能只以 `shader.isSupported` 作为验收。
- 正式启动日志：`H:\MGFR\DialogueRenderRepair-20261020\Logs`。`player-…-exit.json` 是进程退出码；`session-….jsonl` 是 XR 与应用生命周期记录。
- 覆盖前六个文件的备份及 SHA256：`Activation/backup-receipt.json`。准确的覆盖／新增范围与部署哈希：`Activation/activation-receipt.json`。

原始日志和失败的中间探针已保留。`Probe-baseline-v1/v2/v3` 的绘制方式不完整，不能用于判定双眼问题；有效旧新包对照是 `Probe-old-package` 与 `Probe-final`，以及上述实际播放器的 32 组验证。
