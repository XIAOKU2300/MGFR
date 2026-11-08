# ZMD 说话 / 交流动作资源盘点 v2

## 结论

ZMD/Assets 中有 15 个 `.anim`、8 个 `.fbx`、0 个 `.vmd` 和 3 个 `.controller`，没有专门的 talk、speak 或 dialogue 动作。`WAIT02` / `WAIT04` 只能作为等待姿势参考，不能称为现成说话动作。

主项目骨架信息已更正：HandCoexist-20261019/Project 当前运行目标是日本名 PMX 骨架，`Data counts.bones=828`；终末地原版 source Avatar 和动作数据是 596 节点。运行时已应用 22 个身体骨骼映射。此前把主项目目标说成 596 节点是错误的。

本次说话动作替换来源是 10 个终末地交流动作，用于替换程序式说话手势曲线。短 ID 为 `arms_crossed`、`ponder`、`point`、`surprised_pose`、`talk_hands`、`introduce`、`scratch_head_start`、`think`、`relax_react`、`settle`。ZMD 中的 WAIT 动作不在这组说话动作里。

## ZMD 候选结论

上一版盘点列出的近似参考仍保留在 [zmd-survey-v1.json](H:\MGFR\SiLLMBridge-20261020\motion-expansion\zmd-survey-v1.json) 中：`Flair` 是未确认语义的短手势参考，`WAIT02`/`WAIT04` 是 idle/wait，`Twist Dance`/`WIN00` 是表现动作，`Idle1`–`Idle4` 各只有约 0.017 秒。它们都没有证据可作为专门说话动作。

## 骨架与播放路径

ZMD Humanoid 和 UnityChan 资源与终末地原版 596 节点源骨架不同，不能直接套到当前 828 节点项目。当前说话动作路径使用终末地原版动作及已应用的 22 个身体骨骼映射；这次不再把 596 节点误写为运行目标。完整 ZMD 资源路径、时长和绑定路径仍见上一版 JSON。

## 当前程序动作位置

- `unity-client/Assets/MGFR/Scripts/Experience/SpeechMotionState.cs`：程序式语音身体/手臂曲线。
- `unity-client/Assets/MGFR/Scripts/Experience/SpokenGestureState.cs`：按句子生成手势线索并映射骨骼。
- `unity-client/Assets/MGFR/Scripts/Experience/Natural/NaturalKeyframes.cs`：代码内 wave、open-palm、point 等关键帧。
- `unity-client/Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs`：组合动作并写入骨骼 Transform。
