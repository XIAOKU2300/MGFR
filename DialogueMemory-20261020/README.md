# MGFR 对话升级

继续双击 `H:\MGFR\启动MGFR.cmd`。本次在入口实际使用的 `DialogueRenderRepair-20261020\Final-v3` 上合入；保留现有手势面板、渲染修复、衣物缩放、换肤、动作、表情和原音色配置。正在运行的其他程序不会被强制关闭；新功能随下一次从此入口启动生效。

最终启动链为 `启动MGFR.cmd → DialogueRenderRepair-20261020\launch_final.py → DialogueMemory-20261020\launch_memory.py`。原启动器和入口保留，原启动器的普通启动、桌面启动和检查转入新服务，旧 `--worker` 功能继续可用。同期的头显会话恢复修复已合并保留。

## 已接入的功能

- 长期记忆：Mem0 OSS + 本地 Qdrant + 中文 BGE 向量模型。用户明确表达的偏好、称呼、约定和计划在后台提取，跨会话保存。角色自己说的台词、触摸/注视/临时衣物状态不作为用户长期事实。用户的新明确陈述优先于旧偏好。
- 角色资料：同一套本地语义检索，使用独立资料集合。初始六条来自项目已有角色设定，标记本地来源，未冒充官方考据。原角色主提示词继续保留。
- 交互参数：固定身体区域的头显朝向、手部接触/抓握，以及实际衣物穿脱回调。向 LLM 注入中文参数，例如“玩家观看位置：左大腿”。同时区分当前衣物状态和刚才发生的穿脱事件。
- 说话期间按顺序排队，等对应回合的客户端播放完成后再回应；空闲时短暂合并交互后触发回应。用户开口优先，可以打断角色；交互不会伪造成用户说过的话。

观看位置用头显朝向近似，并非眼动追踪。接触区域由骨骼上的胶囊区域与手部追踪位置估计，适用于固定范围语义，不是逐三角形触碰判定。采集器只读取状态，不新增碰撞力、布料约束或骨骼写入。

## 流畅性约束

每轮检索最多等待 120 毫秒，失败或超时直接继续正常对话。最多注入 4 条用户记忆和 3 条角色资料，每条限制长度；后台记忆提取遇到前台对话会让出请求机会。中文向量推理使用 CPU 两线程，不占语音模型的 GPU。

原 GPT-SoVITS 首次计算参考音频曾实测约 41 秒。启动器现在在启动角色前先进行一次静音预热，完成后才允许进入；预热不调用聊天 LLM、不播放声音、不写入对话记录。完全冷启动仍需要等待准备提示，预热不是省去模型加载时间。已有语音质量检查继续保留；远端模型、网络和语音重试也会影响实际等待。

## 管理资料和记忆

角色资料文件：`H:\MGFR\DialogueMemory-20261020\src_v3\knowledge.zh.json`。每项保留唯一 `id`，填写 `text`、`source` 和可选 `keys`。服务启动后可执行下方资料重载；相同 ID 会更新，移出的条目停止参与检索，恢复相同 ID 不会重复导入。不需要重建向量库。

在本目录打开终端，使用原有 Python：

```powershell
& 'H:\MGFR\dialogue-service\.venv\Scripts\python.exe' -B -X utf8 '.\manage_memory.py' list
& 'H:\MGFR\dialogue-service\.venv\Scripts\python.exe' -B -X utf8 '.\manage_memory.py' search '我喜欢喝什么？'
& 'H:\MGFR\dialogue-service\.venv\Scripts\python.exe' -B -X utf8 '.\manage_memory.py' remember '我喜欢清淡的乌龙茶。'
& 'H:\MGFR\dialogue-service\.venv\Scripts\python.exe' -B -X utf8 '.\manage_memory.py' forget '<list 返回的记忆 ID>'
& 'H:\MGFR\dialogue-service\.venv\Scripts\python.exe' -B -X utf8 '.\manage_memory.py' reload-knowledge
```

`remember` 返回已进入后台队列，并不表示已经完成提取。`forget` 让指定记忆停止被检索，本地 Mem0 历史审计仍保留旧版本。界面暂不包含记忆编辑面板。

持久数据在 `Data`（用户向量、角色资料向量、队列和历史库），中文模型在 `Models`；需要备份时在服务退出后复制整个 `Data`。`Data\local-auth.token` 是本机服务凭据，不要分享。记忆文本和提取请求仅在本机持久化/转发，但提取仍调用原先配置的远端 LLM；这里没有改成完全离线聊天。

## 运行位置

| 项目 | 路径或地址 |
|---|---|
| 启动代码 | `H:\MGFR\DialogueMemory-20261020\launch_memory.py` |
| 当前程序/原有功能 | `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\Player\MGFR.exe` |
| 当前交互模块源码 | `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\Source` |
| 记忆与队列代码 | `H:\MGFR\DialogueMemory-20261020\src_v3` |
| 原语音修复 | `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\Voice` |
| 语音 / 动作 / 记忆 | 本机 `8779` / `18772` / `18780` |
| 原 GPT-SoVITS | 本机 `9880`，沿用现有模型和参考音频 |
| 依赖完整版本 | `requirements-lock.txt`，独立 `.venv` |
| 原文件备份和激活记录 | `Activations` 下对应时间目录 |

记忆 API 仅监听回环并要求本机令牌；原 LLM 密钥继续由原语音引导程序读取，未复制到新配置或记忆服务。模型文件已下载到本地并校验 SHA256，正常启动不再联网下载模型。旧语音服务不被终止，端口冲突或发现不匹配版本会停止本次启动并保留已有进程。

## 验证范围

验收结果索引见 `acceptance-final.json`，每份报告保留其实际测试方式和计时。最终三轮真实对话首段音频为 4.60 / 5.24 / 2.53 秒，其中记忆检索为 13.60 / 29.36 / 24.02 毫秒。独立记忆检索五次为 3.69–4.74 毫秒；这些是本机测量值，不代表远端服务响应上限。

另外针对实测的“墨魉→墨量/墨两”识别异字做了限定归一，避免角色专名触发无意义的语音重试；没有替换语音文本或降低原质量阈值和数字检查。

已测试真实 Mem0 持久化、中文语义检索、隔离与幂等、断线重试、资料更新/停用/恢复、记忆删除、检索超时降级；还使用独立 Unity 程序验证实际骨骼区域查询、衣物脱下/穿回回调、HTTP 参数和原手势面板。真实 LLM 与原音色的连续对话测试接收了 PCM 音频，但没有打开麦克风或向头显播放。

尚未替代佩戴 Pico 后的实机验收：身体区域边缘、手部遮挡、真实穿脱手感以及长时间对话的主观体验仍需在头显里观察。当前用户运行的程序不会被本次验收关闭。

上游来源：[Mem0](https://github.com/mem0ai/mem0)、[FastEmbed](https://github.com/qdrant/fastembed)、[BGE 中文模型](https://huggingface.co/BAAI/bge-small-zh-v1.5)。本次锁定版本及模型下载校验分别保留在版本清单和 `Models\bge-small-zh-manual-v1\download-verification.json`。
