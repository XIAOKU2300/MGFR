# 同一套祀 v4：准备独立布料程序

工具只支持 profile 指纹对应的已转换网格，以及已有 ZMD/换肤 API 的 MGFR 项目。它只创建新目录，不覆盖宿主、输入模型或已有输出，不启动 Unity 和服务。原 EFMI 转换模式保持原工具，不必重跑。

先只读核查：

```powershell
python scripts/prepare_interaction_candidate.py --client 'H:\MGFR\unity-client' --skin 'H:\MGFR\converted\skins\si-swimsuit-barefoot-ankle-v4' --inspect
```

生成新项目，输出名由调用时选定，不能重复使用已有目录：

```powershell
python scripts/prepare_interaction_candidate.py --client 'H:\MGFR\unity-client' --skin 'H:\MGFR\converted\skins\si-swimsuit-barefoot-ankle-v4' --out 'H:\MGFR\ClothCandidate-new'
```

它复制 Assets、Packages、ProjectSettings，替换新副本内的目标皮肤数据，加入自写 XPBD 代码和独立构建入口，并在新副本的 `BareHandInteraction.cs` 接入所有权回调。输入 hash 与候选接入信息记录到输出的 `cloth-preparation.json`。宿主 API 或网格指纹不匹配就停止；不要删除检查来硬套。

构建使用本机已有 Unity Editor，命令中的路径仅为本案例示例：

```powershell
$env:ALLUSERSPROFILE='C:\ProgramData'
$clothBuild=Start-Process -FilePath 'H:\MGFR\Editor\Unity.exe' -ArgumentList '-batchmode -job-worker-count 2 -projectPath H:\MGFR\ClothCandidate-new -executeMethod SwimsuitClothBuild.Build -logFile H:\MGFR\cloth-build-new.log' -WindowStyle Hidden -PassThru
$clothBuild.WaitForExit()
$clothBuild.ExitCode
```

Windows GUI 程序直接调用可能提前返回，用实际进程等待完成。需要 IPC/GPU/授权目录权限时走环境正常的权限机制，不去改用户的运行时注册表。`ALLUSERSPROFILE` 是本机 UPM 曾缺失的环境兼容处理，不是跨机器必需步骤。

默认只做一次短启动/往返换肤检查。程序参数 `-mgfr-skins -mgfr-skin swimsuit -mgfr-zmd` 启用皮肤和渲染，附加 `-mgfr-cloth-check -mgfr-cloth-output <新报告路径>` 才会自动检查并退出。桌面用 `-mgfr-noxr`；若 XR 预初始化仍等待头显，可仅给该测试子进程一个不存在的 `XR_RUNTIME_JSON` 路径，不改变用户全局 XR 配置。

正式头显启动不传测试标志和错误 XR 路径。交付新入口，指向这个新项目实际生成的 `Build/Windows/MGFR.exe`。F5 换肤、F7 物理、F11 风格。

若用户要求合入主项目，先准备确切补丁和原件备份，再按本次会话的覆盖授权执行；本工具不会代替该步骤。
