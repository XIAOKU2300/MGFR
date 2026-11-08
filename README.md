# MGFR

**在真实房间里，与虚拟角色自然交谈和互动。**

MGFR 是一个面向 Windows、Unity 和 PICO / ALVR 的个人混合现实角色项目。它将中文语音对话、长期记忆、结构化动作与表情、手部交互和角色渲染接到同一条运行链中。

*An experimental mixed reality character companion with Chinese voice dialogue, memory, expressive motion and hand interaction.*

> **当前阶段：初步源码公开候选。暂不提供安装包、预编译客户端或一键部署。**
>
> 本候选从已同步的 MGFR 源码导出，不携带原私有仓库的提交历史。当前运行版本由下方启动链确定。完整角色体验依赖使用者自行取得合法授权的模型、贴图、动画、语音资源和本地配置。MagicaCloth 2 插件源码已从本快照排除；ZMD 参考及移植代码按维护者确认的原作者许可保留，独立于本项目 MIT 授权。见 [源码检查](docs/OPEN_SOURCE_REVIEW.md) 和 [第三方声明](THIRD_PARTY_NOTICES.md)。

## 可以做什么

| 能力 | 当前实现 |
| --- | --- |
| 中文语音对话 | VAD → SenseVoice ASR → 兼容 OpenAI 协议的 LLM → GPT-SoVITS TTS；支持多轮历史、结构化回复、错误恢复和取消 |
| 动作与表情 | LLM 输出台词、情绪、强度、表情变体及动作时间表；身体动作与口型、眨眼、情绪叠加协作 |
| 语音与动作同步 | 按实际音频播放进度推进动作的进入、循环和退出；等待合成时不提前走动作时间 |
| 长期记忆与角色资料 | 用户事实和角色资料分别保存、检索；检索超时降级，支持资料更新、停用和记忆管理 |
| 交互上下文 | 读取手部接触、抓取及衣物状态；事件合并、排队、冷却和过期处理，用户发言优先 |
| 手势面板 | 稳定握拳约 3 秒召唤，松拳后用食指触控；支持追踪丢失及抓取互斥 |
| 角色体验 | 本地皮肤切换、衣物与鞋子穿脱、等比缩放、布料与手部互动、字幕及 XR 恢复 |

当前本地目录包含 **83 段动作元数据，其中 62 段可供 LLM 调用；45 个兼容表情、8 类情绪**。这些是 2026-11-08 核对的本地资源目录信息，**动作二进制、角色模型与表情资源不随源码提供**。角色身体动作经过目标骨架映射，不表示完整重放游戏原始骨架和全部面部骨骼。

## 当前状态与边界

- 完整运行链已有本机验证记录；语音连通、桌面回放、合成事件和头显实测分别记录，不互相替代。历史验收见 [当前版本](docs/CURRENT_PROJECT.md) 和 [体验修复](docs/experience-repair-20261021.md)。
- 本轮同步的源码更新对应已安装的 `experience-repair-20261021-v1`：降低无效交互请求、按播放样本调度动作、改进透明衣物覆盖，并减少布料计算的重复工作。
- 注视使用**头显朝向近似**，不是眼动追踪；观看区域只作为用户下一次发言的上下文，不独立触发回复。
- 播放期间保留回声保护；尚不能宣称已完成 AEC 或任意时刻的自然语音插话。
- 本地存储不代表完全离线：对话和记忆提取可以调用用户配置的远端 LLM；可选远程向量检索还需单独配置，查询文本默认不发送。
- PICO 内观感、ALVR 编码后的透明边缘、真实麦克风及长时间互动仍需实机验收。连续 TTS 与双手布料压力场景仍有性能余量不足，暂无全场景帧率保证。
- **目前没有从干净克隆直接重建完整现用客户端的一键构建流程。** 仓库中的早期 Unity 项目、当前附加模块、资源导入和本机打包脚本还在整理。

## 源码入口

当前日常启动链为：

```text
启动MGFR.cmd
  → DialogueRenderRepair-20261020/launch_final.py
  → DialogueMemory-20261020/launch_memory.py
  → DialogueRenderRepair-20261020/Final-v3/Player/MGFR.exe  [本地构建，不入库]
```

| 位置 | 用途 |
| --- | --- |
| `DialogueRenderRepair-20261020/Final-v3/Source/` | 当前动作、交互、布料、手势和渲染附加模块 |
| `DialogueRenderRepair-20261020/Final-v3/Voice/` | 当前结构化回复、语音分句、质量检查和 TTS 适配 |
| `DialogueRenderRepair-20261020/Final-v3/ShaderSource/` | 当前覆盖与字幕修复的着色器构建源码；ZMD 派生部分适用第三方授权 |
| `DialogueMemory-20261020/src_v3/` | 当前记忆服务、角色资料检索和交互事件调度 |
| `SiLLMBridge-20261020/client/` | 本地结构化动作接口的客户端示例 |
| `dialogue-service/` | 可独立测试的基础 WebSocket 对话服务及模拟引擎 |
| `unity-client/` | 早期 Unity 基础工程和协议实现；不等同于现用完整客户端 |
| `tools/` | 离线模型转换、资源排除检查及仓库工具 |
| `docs/` | 当前版本、协议、验收、资源边界和设计记录 |

其他日期目录和 `src_v1` / `src_v2` 保留开发参考。阅读当前实现时以本节路径为准；`Current`、`Final` 或文件夹日期本身不是版本依据。

## 先运行不依赖模型的对话服务

这条路径用于开发与协议检查，不会加载角色、连接头显或调用真实 LLM / TTS。需要 Python 3.11+；当前开发机使用 Python 3.12。

在仓库根目录打开 PowerShell：

```powershell
cd .\dialogue-service
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:MGFR_CONFIG = (Resolve-Path .\config.stub.toml).Path
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

另开终端，在 `dialogue-service` 目录运行协议客户端：

```powershell
& .\.venv\Scripts\python.exe -m app.smoke_client
```

模拟模式使用固定识别文本、固定回复和测试音。它可以验证 WebSocket 消息和音频传输，不代表真实语音识别或角色对话。

运行基础测试：

```powershell
$env:MGFR_CONFIG = (Resolve-Path .\config.stub.toml).Path
& .\.venv\Scripts\python.exe -m pytest -q
```

`config.example.toml` 是真实引擎的配置参考，不能当作纯模拟配置；请使用新增的 `config.stub.toml` 完成上面的检查。

## 接入完整本地体验

当前完整体验面向 **Windows x64、Unity 6000.3.26f1、SteamVR / OpenXR 和 ALVR**。PICO 4 是已有硬件参考，不代表其他设备已通过适配。

1. 先阅读 [资源策略](docs/asset-policy.md) 与 [第三方声明](THIRD_PARTY_NOTICES.md)，自行准备有权使用的角色、动作和语音资源。
2. 根据 [模型转换说明](tools/model-conversion.md) 和已有离线工具准备本地数据；转换产物继续留在 Git 之外。
3. 分别配置真实 ASR、LLM、GPT-SoVITS 和记忆依赖。密钥使用本机配置或环境变量，禁止写入源码与问题报告。
4. 按当前源码入口核对工程和构建依赖。根启动脚本包含原开发机的绝对路径，干净克隆后不能直接双击使用。
5. 先做桌面与协议检查，再单独验收头显音频、麦克风、透明背景和交互。

当前开发环境的语音、动作、记忆和原 TTS 服务分别使用回环端口 `8779`、`18772`、`18780`、`9880`；基础模拟服务使用 `8765`。这些是现有运行约定，不是要求公开到局域网或互联网的服务端口。

## 初步开源范围

本阶段整理源码、配置模板、协议、转换工具和验证方法。**暂不发布安装包、Unity Player、预编译 DLL、着色器包、容器镜像或任何角色资源包。**

不提交或分发：

- 游戏或第三方角色模型、贴图、原始与转换动画、网格和材质数据。
- 语音权重、参考录音、生成语音及 ASR / 向量模型文件。
- API 密钥、认证令牌、真实配置、聊天记录、长期记忆数据库及个人日志。
- Unity / SteamVR / ALVR 安装目录、构建结果、缓存和未经许可的商业插件源码。

本候选使用不含旧提交历史的新源码快照，排除了参考工程附带的 MagicaCloth 2 插件和内部工作记录。维护者已确认 ZMD 原作者允许本项目改编及源码再分发；该确认不将第三方代码重新许可为 MIT。ZMD 参考目录不包含原工程的商业插件和角色资源，不能视为完整可直接运行的示例工程。详见 [检查与后续事项](docs/OPEN_SOURCE_REVIEW.md)。

## 文档与参与

- [当前项目与运行版本](docs/CURRENT_PROJECT.md)
- [本轮体验修复及验证限制](docs/experience-repair-20261021.md)
- [基础通信协议](docs/protocol.md)
- [资源与隐私边界](docs/asset-policy.md)
- [贡献说明](CONTRIBUTING.md) · [安全问题报告](SECURITY.md)

早期 [架构](docs/architecture.md)、[验收](docs/acceptance.md) 与 [环境](docs/environment.md) 保留阶段记录，具体实现和状态可能早于当前版本。

## 许可与致谢

由本项目有权授权的原创源码采用 [MIT License](LICENSE)，允许依照该许可证使用、修改和分发，包括商业使用。

第三方代码、Unity 包、游戏 IP、角色和声音资源分别受其原许可或权利约束，不因本项目选择 MIT 而改变。授权边界、保留的声明和 ZMD 许可确认记录见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

感谢 Unity、ALVR、SteamVR / OpenXR、GPT-SoVITS、SenseVoice / sherpa-onnx、Silero VAD、Mem0、Qdrant / FastEmbed、BGE 和 Qwen 等上游项目。MGFR 是个人实验项目，与相关游戏、硬件及上游项目不存在官方关联。
