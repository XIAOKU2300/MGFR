# ZMD 说话 / 交流动作资源盘点

## 结论

在 `H:\MGFR\ZMD\Assets` 中排除 `Library`、`Packages` 后，找到 15 个 `.anim`、8 个 `.fbx`、0 个 `.vmd` 和 3 个 `.controller`。没有名称或控制器状态明确标为 talk、speak、dialog、gesture 的动作。最接近的只是 `Flair` 和两个 `WAIT` 待机片段，语义需要预览确认；不能据此称为现成说话动作。

主项目当前不是通过 Unity `Animator` 播放 `.anim`。说话时由 `SpeechMotionState` 生成低幅身体/手臂动作，`SpokenGestureState` 根据语句计划手势，`NaturalGestureLibrary` 提供代码内关键帧，最终由 `IdleMotionPlayer` 写入 596 节点骨骼。

## 候选参考

| 资源 | 时长 | 证据与用途判断 | 与终末地 596 骨骼兼容性 |
|---|---:|---|---|
| `Char\Animation\Flair.anim` | 1.00 秒 | 主角色 Animator 状态名；像短姿态/手势参考，但语义未预览 | Humanoid 肌肉曲线，没有终末地节点路径；需 Avatar/重定向播放链路 |
| `...\UnityChanKAGURA\Animation\WAIT02.anim` | 8.30 秒 | `SD_UnityChan.controller` 状态；等待/待机，不是说话 | 171 条 Transform 路径，`Character1_Reference/Character1_Hips/...`；异源骨架，需重定向 |
| `...\UnityChanKAGURA\Animation\WAIT04.anim` | 5.17 秒 | `SD_UnityChan.controller` 状态；等待/待机，不是说话 | 181 条 Transform 路径，`Character1_Reference/Character1_Hips/...`；异源骨架，需重定向 |
| `Char\Animation\Twist Dance.anim` | 9.43 秒 | 主角色控制器状态；舞蹈而非对话 | Humanoid 肌肉曲线；需 Avatar/重定向 |
| `...\UnityChanKAGURA\Animation\WIN00.anim` | 3.97 秒 | UnityChan 胜利动作（文件在目录中；控制器状态未找到） | 120 条 Character1 层级路径；异源骨架，需重定向 |
| `Char\Animation\Idle1.anim` | 0.017 秒 | 主角色控制器 Idle 状态 | Humanoid 曲线；仅 1 帧，不能作为持续待机循环 |
| `Char\Animation\Idle2.anim` | 0.017 秒 | 主角色控制器 Idle 状态 | Humanoid 曲线；仅 1 帧，不能作为持续待机循环 |
| `Char\Animation\Idle3.anim` | 0.017 秒 | 主角色控制器 Idle 状态 | Humanoid 曲线；仅 1 帧，不能作为持续待机循环 |
| `Char\Animation\Idle4.anim` | 0.017 秒 | 主角色控制器 Idle 状态 | Humanoid 曲线；仅 1 帧，不能作为持续待机循环 |

完整路径、绑定路径、控制器引用与证据见本目录的 `zmd-survey-v1.json`。

## 当前程序动作位置

- `unity-client/Assets/MGFR/Scripts/Experience/SpeechMotionState.cs`：根据音频说话状态计算程序式身体/手臂偏移。
- `unity-client/Assets/MGFR/Scripts/Experience/SpokenGestureState.cs`：从句子队列规划手势，叠加手势姿态。
- `unity-client/Assets/MGFR/Scripts/Experience/Natural/NaturalKeyframes.cs`：内置 wave/open-palm/point 等手势曲线。
- `unity-client/Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs`：将 idle、speech 和手势组合后写入当前角色的骨骼 Transform。

## 兼容性判断

ZMD 的陈千语 FBX 元数据显示 `animationType: 3`、Humanoid Avatar 设置，骨架从 `陈千语(Clone)/U_Char/.../joint_HipMaster` 开始。UnityChan 等待动作绑定的是 `Character1_Reference/Character1_Hips/...`。主项目则使用终末地来源的 596 节点骨架与自定义 ENFMOT1 播放/逐骨写入路径，没有发现可直接消费这些 `.anim` 的 Animator/Avatar 绑定。它们都不能直接替换现有说话动作；Humanoid 片段仍需先建立并验证目标 Avatar 播放链路，显式路径片段还需确认重定向映射。

本盘点只读检查 Unity YAML 与 FBX `.meta`，未打开 Unity、未预览动作、未转换资源。
