# SiLLMBridge Python 客户端

`llm_chat.py` 使用 Python 标准库连接 OpenAI 兼容聊天接口，再把模型返回的 JSON 计划交给本机 SiLLMBridge。默认本地服务地址是 `http://127.0.0.1:18772`。客户端不执行模型返回的代码，也不接受模型提供的 URL。

## 配置与运行

在 PowerShell 中设置模型服务变量后运行：

```powershell
$env:SI_LLM_BASE_URL = 'https://你的兼容接口/v1'
$env:SI_LLM_MODEL = '你的模型名'
$env:SI_LLM_API_KEY = '你的密钥'
& 'C:\Program Files\Python312\python.exe' -X utf8 .\llm_chat.py --message '你好'
```

`SI_LLM_API_KEY` 可省略；客户端不会打印密钥、请求头或第三方错误正文。若本地服务不在默认地址，可设置 `SI_LLM_SERVICE_URL`。支持 `--dry-run`（照常调用模型并解析 JSON，但不请求 `/v1/perform`）和 `--no-response-format`（不向模型接口发送 `response_format: {"type":"json_object"}`）。默认不做纠正重试。

## 本地演示

演示只请求本地服务，不访问模型提供方：

```powershell
& 'C:\Program Files\Python312\python.exe' -X utf8 .\llm_chat.py --demo
```

固定演示计划为 `emotion: happy`、`emotion_intensity: 0.65`、`expression: auto` 和 `wave` 动作。最终执行动作以服务响应的 `effective_plan` 为准。

## JSON 约定

模型消息使用 `/v1/context` 返回的 `system_prompt` 与 `json_schema`，并附上 `/v1/catalog` 的动作和情绪目录。模型必须返回未经 Markdown 包装的 JSON 对象，字段至少包括：

```json
{"version":1,"text":"你好","emotion":"happy","emotion_intensity":0.65,"expression":"auto","actions":[{"name":"wave","at":0}]}
```

`emotion` 必须是 `neutral`、`happy`、`sad`、`angry`、`surprised`、`shy`、`thinking`、`affection` 之一；`emotion_intensity` 为 0 到 1，缺省按 0.65 处理。`expression` 可为 `auto`（缺省值，由服务按 emotion 选择变化表情）或 `native`（不叠加情绪表情；当前PMX运行包不重放原生97脸骨）。最多安排 3 个动作，时间 `at` 为 0 到 60 秒并按升序排列；服务端会拒绝 catalog 中不存在的动作，并执行防重复处理。允许 `actions: []`，模型可在适合时不安排动作。客户端会拒绝非 JSON、Markdown 包装、非对象和明显不合法的基本字段，不会将其发送给本地服务。

`--demo` 也发送完整情绪字段：`happy`、强度 `0.65`、`auto` 与 `wave`。

## 文本与外部 TTS

本客户端不提供 TTS。需要语音时，可把同一次 `/v1/perform` 响应中 `effective_plan.text` 交给外部 TTS，并使用该次响应对应的动作计划同步播放；动作时间从服务接收这次 perform 请求时开始计时。不要用模型原始文本替代 `effective_plan.text`，因为服务返回的最终计划是同步依据。

## 本地测试

测试只启动 loopback 上的临时假 HTTP 服务，不连接真实模型、不需要凭据：

```powershell
& 'C:\Program Files\Python312\python.exe' -X utf8 -m unittest -v .\test_llm_chat.py
```
