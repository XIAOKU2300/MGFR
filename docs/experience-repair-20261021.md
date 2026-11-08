# MGFR 体验修复 experience-repair-20261021-v1

现有日常入口和端口不变。原ASR/LLM/TTS配置、音色、长期记忆、模型、贴图和166份动作资源不在应用清单中。当前动作仍保存83段，实际LLM有效目录62段；没有开放备用动作或恢复脚踝拟合。

- 绿幕薄纱取消Bayer网点，保留纹理镂空；对不透明角色几何保留透视，外轮廓采用稳定覆盖。普通相机的材质比较最大像素误差0。手部仍是独立深度遮挡，未替换手部Shader。实际头显/ALVR编码、远距离边缘与发白仍待佩戴验收。
- 原生动作按已有source_name配对进入/循环/退出；按实际DSP播放样本计时，排除TTS等待，支持正常结束、用户取消与换肤相位。源姿态、速度和绑定数据保持原样。
- 观看区域是头显朝向近似，仅为下一次用户发言提供上下文；旧客户端gaze事件也无法独立触发LLM。明确互动保留500ms合并、6秒冷却、1.5秒空闲、30秒TTL和用户开口优先；衣物当前状态独立保存。原JSON与本地接口兼容。
- 缓存XPBD拓扑/胶囊计算、复用缓冲与私有方法委托，减少重复材质扫描和逐帧分配；最终投影按独立粒子收敛退出，未减少约束或关闭物理。120步与原算法的最大位置差约3.18e-7米，最终投影误差0。
- 启动器只对自己新建的TTS进程使用BelowNormal与4逻辑CPU预算；当前16逻辑CPU上实测可减少长帧，已有外部TTS服务不改动。首次预热可能变慢。连续合成＋双手仍未达到11ms主线程P95目标；不承诺全部场景已流畅。

## 性能证据

同机72Hz桌面。主线程数据采用Unity cpuMainThreadFrameTime；cpuFrameTime另含等待，不能混为渲染工作。GPU时间无有效样本，不能当作GPU达标。旧基线使用同样编译选项和测量器；旧版缺少start/end导致新动作图检查失败属于预期。

|版本|场景|主线程P95 ms|布料P95 ms|每帧分配P95 字节|>28ms帧|
|---|---|---:|---:|---:|---:|
|旧基线|idle-swimsuit|12.01|9.50|16628|0/180|
|旧基线|state-family-swimsuit|11.88|9.67|16776|0/937|
|旧基线|motion-original|4.17|8.16|16230|0/180|
|候选|idle-swimsuit|9.14|6.06|8536|0/180|
|候选|state-family-swimsuit|9.25|6.17|8536|0/937|
|候选|motion-original|4.21|0.00|8666|0/180|
|候选|two-hand-cloth-grab|10.20|6.42|9248|0/180|
|候选＋连续真实TTS（4逻辑CPU）|idle-swimsuit|9.38|6.15|8536|0/180|
|候选＋连续真实TTS（4逻辑CPU）|state-family-swimsuit|10.90|6.79|8942|0/926|
|候选＋连续真实TTS（4逻辑CPU）|motion-original|4.31|0.00|8728|0/180|
|候选＋连续真实TTS（4逻辑CPU）|two-hand-cloth-grab|17.50|9.18|9248|0/180|

连续TTS为不停重复固定句的压力负载。环境线程=2与单纯降优先级没有稳定改善，未作为正式策略；后续IDLE策略在预热时遇到原TTS的ONNX内存分配失败，未获验证，生产调用不启用IDLE。失败日志保留。真人对话/ASR、Pico听感与头显串流仍未验收。

## 验证与诊断

实际Session/ASGI和虚拟600秒注视：额外LLM请求0；取消、顺序、冷却、过期、旧回包与重连通过。实际Unity动作、双手关节回放的接触/双手抓布料/丢失释放通过。真实祀32kHz音频经Unity WebSocket、PCM、DSP、表情与动作联调通过（静音桌面、固定LLM）。0.2–4倍缩放及脱下衣物比例通过；100秒双眼GPU/换肤/缩放/XR退出保护结果见本地报告。

`-mgfr-perf-out <新的绝对jsonl路径>`可启用5秒汇总的异步数值日志。可运行本次检查目录中的collect_alvr.py只读订阅ALVR数值事件，忽略Session/Log/Tracking；本次连接成功但没有串流统计样本。

ALVR字段和只读事件接口核对自 [v20.14.1事件定义](https://github.com/alvr-org/ALVR/blob/v20.14.1/alvr/events/src/lib.rs) 与 [Web服务源码](https://github.com/alvr-org/ALVR/blob/v20.14.1/alvr/server_core/src/web_server.rs)。

## 生效和回退

唯一日常入口仍为H:/MGFR/启动MGFR.cmd。实际载入路径仍为Final-v3/Player和DialogueMemory-20261020/src_v3。应用前必须核对application-manifest.json及候选校验值，并收到用户针对完整清单的覆盖确认。安装后以ApplicationBackup目录中的applied.json和已安装校验值为准；当前文件本身不构成应用或上传授权。

源文件备份在本次检查目录的Baseline；应用工具会再保存当时逐文件备份。回退亦需列清单并确认，且先核对当前版本，不能拿旧备份覆盖并发新改动。全程没有GitHub上传。
