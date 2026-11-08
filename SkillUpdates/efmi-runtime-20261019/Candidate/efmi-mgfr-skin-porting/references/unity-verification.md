# 独立 Unity 验证

## 准备

脚本不附带用户的 Unity Loader、Shader 或模型。使用目标项目实际的 `SiCharacterLoader.cs`、`SiModelData.cs`、`MgfrCharacter.shader` 来创建新的验证项目：

```powershell
python scripts/prepare_probe.py --client 'H:\MGFR\unity-client' --out 'H:\MGFR\converted\new-skin-probe'
```

只复制必要源文件与 ProjectVersion、ProjectSettings 到新路径，不复制 Library、运行时自动安装组件、业务服务或整个工作项目。验证入口在 skill 的 `scripts/unity/` 中。若目标项目 Loader 已变更并出现编译依赖，检查实际依赖后在隔离项目补充最小源代码，不修改工作项目来迁就探针。

## 运行

```powershell
& 'H:\MGFR\Editor\Unity.exe' -batchmode -noUpm -projectPath 'H:\MGFR\converted\new-skin-probe' -executeMethod BarefootProbe.Run -skinRoot 'H:\MGFR\converted\new-barefoot-run\model' -probeDir 'H:\MGFR\converted\new-foot-review' -logFile 'H:\MGFR\converted\new-foot-probe.log'
```

普通泳装用 `SwimsuitProbe.Run`。图片目录和日志路径都使用新路径。`-noUpm` 是本机 Package Manager IPC/undefined-path 出错后的离线验证办法，不是修改包配置或修复 UPM 本身。若环境不允许 IPC、缓存写入或 GPU，使用宿主的正常权限机制；不要因此改动生产项目。失败次数有界，保留日志并说明原因。

本案例 Unity 6000.3.26f1 已运行这些入口。版本变化后检查 API 兼容性，不据旧日志宣称新版本通过。

## 探针实际证明的内容

- 用真实 Loader 生成 Mesh、Material、全部骨骼和 40 个形变。
- BakeMesh 静止顶点与模型顶点比较，最大误差阈值 0.1 mm。
- 渲染正/背/侧/斜面；修改实际手臂、腿部骨骼；驱动 `まばたき` 和 `あ`；检查几何确实发生变化。
- 赤脚入口额外拍摄脚部侧面、正面、双脚斜面。

探针固定动作只是绑定烟测，不是所有动作穿模检查，不是完整 idle/追踪交互，也不是 VR 实机验收。基础 Shader 渲染不证明原项目风格化渲染器已支持该皮肤的 normal/packed/emission。

生成图片后必须用实际图片查看工具打开。读取文件名、图片数量或运行 exit code 都不足以验收贴图与自然度。
