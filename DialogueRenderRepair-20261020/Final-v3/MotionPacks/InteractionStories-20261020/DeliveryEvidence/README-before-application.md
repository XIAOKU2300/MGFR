# 祀：剧情与互动动作资源包

状态：资源保存及适配完成；主项目已有文件尚未覆盖。

当前目标按 `H:/MGFR/启动MGFR.cmd` 实际解析为 `H:/MGFR/DialogueRenderRepair-20261020/launch_final.py` → `Final-v3/Player/MGFR.exe`。本目录是动作资源包，不是新的运行入口。

- 57段新增源动作：53段祀剧情/对话动作，4段通用女性touchhead/petting。保留完整原生596节点数据与来源证据。
- 已烘焙两套当前皮肤，共114份58骨目标姿势；43段准备加入调用目录，14段作为备用。
- 21个新增面部形态变体，覆盖7种情绪；加上原有24个，共45个。生气类仍沿用原3个，其余每类6个。
- 保存12份原生97脸骨预设（其中7个是本次新筛出的原预设），以及源控制权重、2帧596节点文件和哈希；这些归档文件未接入当前PMX面部接口。
- 6组三阶段动作搭配建议，start→loop→end边界最大旋转差小于0.23度。

## 重点互动资源

`common_touchhead_start / loop / end` 已适配；原名支持触头相关用途，但原剧情中的施受方向尚未确认，作为互动候选保留。`common_petting_loop` 画面显示手向身前伸出，且原片段带约一米固定场景偏移；交付副本已去掉固定水平偏移，原始副本保留，未加入日常随机池。

摸头相关表情可参考 `happy_headpat_received`、`shy_headpat`、`affection_relaxed_nearby`、`affection_warm_response`。这是原预设意图的手工兼容形态组合，不是原生97脸骨一比一重放。

具体动作名字与三阶段时间表见 `interaction-recipes.json`；里面的事件仅为搭配建议。本次没有修改手部触摸检测、事件绑定、TTS、对话历史、渲染、材质、布料或缩放。

## 已完成检查

- 当前三份模型JSON与烘焙参考版本逐字节相同，两个skin的原idle姿势也相同。
- 114份目标姿势的帧数、fps、58骨索引、完整字节数、有限值和四元数范数均通过。
- 在最新版Final-v3的隔离副本中实际采样57段动作并渲染45份面部预设。检查只涉及离线本地播放，未调用远端LLM。
- 62个允许动作（原19 + 新43）通过离线Bridge调用；表情选择不重复最近两次变体，45个变体均覆盖到。
- 没有逐帧宣称衣物零穿插，也没有进行头显实机触摸验收。

## 目录

- `Adapted/motions/`：57份原生动作及manifest。
- `Adapted/native-actions/{swimsuit,original}/`：当前格式可用的烘焙身体动作。
- `faces/expressions-additions.json`：21个当前接口可用的表情变体。
- `faces/native-bone-poses/`：12份原始97脸骨姿势归档。
- `interaction-recipes.json`：6组身体动作和情绪搭配。
- `source-archives.json`：原始提取、VFS校验、ACL采样及来源收据位置。
- `latest-validation.json`、`Adapted/body-validation.json`：验证结果。
- `InstallReview/`：待批准的5个文件候选及完整备份。

![动作示例](motion-highlights.jpg)

![表情示例](face-highlights.jpg)

## 待应用的范围

要加入当前调用池，需新增171份资源文件，并覆盖下面5个已有文件。现有启动器要求可调用动作恰好19个，所以只需将这项检查同步为62；所有入口、端口和配置保持现值。应用后需重载当前8776/18769的同一语音/动作worker以读取目录。不会停止旧8773/18766或TTS9880。

- 操作：覆盖
  - 目标：`H:\MGFR\SiLLMBridge-20261020\MainData\motions\manifest.json`
  - 影响：1个文件
  - 理由：增加57段动作索引
  - 安全检查：完整备份 `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\MotionPacks\InteractionStories-20261020\InstallReview\Backups\1-manifest.json`；应用前需确认当前SHA256与收据一致。

- 操作：覆盖
  - 目标：`H:\MGFR\SiLLMBridge-20261020\MainData\expressions.json`
  - 影响：1个文件
  - 理由：增加21个面部表情兼容变体
  - 安全检查：完整备份 `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\MotionPacks\InteractionStories-20261020\InstallReview\Backups\2-expressions.json`；应用前需确认当前SHA256与收据一致。

- 操作：覆盖
  - 目标：`H:\MGFR\SiLLMBridge-20261020\MainData\catalog.json`
  - 影响：1个文件
  - 理由：增加动作/表情目录，14段标为备用
  - 安全检查：完整备份 `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\MotionPacks\InteractionStories-20261020\InstallReview\Backups\3-catalog.json`；应用前需确认当前SHA256与收据一致。

- 操作：覆盖
  - 目标：`H:\MGFR\DialogueRenderRepair-20261020\Final-v3\Voice\avatar_json_v2.py`
  - 影响：1个文件
  - 理由：只扩充43个动作名字，不改变对话或TTS逻辑
  - 安全检查：完整备份 `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\MotionPacks\InteractionStories-20261020\InstallReview\Backups\4-avatar_json_v2.py`；应用前需确认当前SHA256与收据一致。

- 操作：覆盖
  - 目标：`H:\MGFR\DialogueRenderRepair-20261020\launch_final.py`
  - 影响：1个文件
  - 理由：现有动作数量检查19改为62，匹配扩充后的目录；入口/端口/配置不变
  - 安全检查：完整备份 `H:\MGFR\DialogueRenderRepair-20261020\Final-v3\MotionPacks\InteractionStories-20261020\InstallReview\Backups\5-launch_final.py`；应用前需确认当前SHA256与收据一致。

## 全部57段新增动作

| 可调用 | 名字 | 标签 | 秒 |
|---|---|---|---:|
| 准备加入 | `story_dialog_single_chesthugging3_talk` | 抱臂说话 | 2.467 |
| 备用 | `story_dialog_single_idle_turn_l_180` | 左转180度 | 2.500 |
| 备用 | `story_dialog_single_idle_turn_l_90` | 左转90度 | 2.500 |
| 备用 | `story_dialog_single_idle_turn_r_180` | 右转180度 | 2.500 |
| 备用 | `story_dialog_single_idle_turn_r_90` | 右转90度 | 2.500 |
| 准备加入 | `story_dialog_state_adjust_loop` | 站姿调整·循环段 | 6.933 |
| 准备加入 | `story_dialog_state_angry02_end` | 不满回应·收尾 | 2.167 |
| 准备加入 | `story_dialog_state_angry02_loop` | 不满回应·循环段 | 2.667 |
| 准备加入 | `story_dialog_state_angry02_start` | 不满回应·起始 | 1.417 |
| 准备加入 | `story_dialog_state_censure_end` | 嗔怪/责备·收尾 | 2.917 |
| 准备加入 | `story_dialog_state_censure_loop` | 嗔怪/责备·循环段 | 3.333 |
| 准备加入 | `story_dialog_state_censure_start` | 嗔怪/责备·起始 | 13.333 |
| 准备加入 | `story_dialog_state_chesthugging1_end` | 抱臂姿态一·收尾 | 2.167 |
| 准备加入 | `story_dialog_state_chesthugging1_start` | 抱臂姿态一·起始 | 1.900 |
| 备用 | `story_dialog_state_chesthugging3_derived_tail_end` | 抱臂·尾部衍生·收尾 | 1.950 |
| 备用 | `story_dialog_state_chesthugging3_derived_tail_loop` | 抱臂·尾部衍生·循环段 | 4.400 |
| 备用 | `story_dialog_state_chesthugging3_derived_tail_start` | 抱臂·尾部衍生·起始 | 1.417 |
| 准备加入 | `story_dialog_state_chesthugging3_end` | 抱臂姿态三·收尾 | 1.950 |
| 准备加入 | `story_dialog_state_chesthugging3_loop` | 抱臂姿态三·循环段 | 4.400 |
| 准备加入 | `story_dialog_state_chesthugging3_start` | 抱臂姿态三·起始 | 1.417 |
| 备用 | `story_dialog_state_cough_end` | 掩口轻咳·收尾 | 2.000 |
| 备用 | `story_dialog_state_cough_loop` | 掩口轻咳·循环段 | 3.600 |
| 备用 | `story_dialog_state_cough_start` | 掩口轻咳·起始 | 2.200 |
| 备用 | `story_dialog_state_dignified_end` | 郑重姿态·收尾 | 2.667 |
| 备用 | `story_dialog_state_dignified_loop` | 郑重姿态·循环段 | 3.333 |
| 备用 | `story_dialog_state_dignified_start` | 郑重姿态·起始 | 3.333 |
| 准备加入 | `story_dialog_state_halfraise_end` | 半举手回应·收尾 | 2.833 |
| 准备加入 | `story_dialog_state_halfraise_loop` | 半举手回应·循环段 | 2.417 |
| 准备加入 | `story_dialog_state_halfraise_start` | 半举手回应·起始 | 2.000 |
| 准备加入 | `story_dialog_state_muse_end` | 沉思·收尾 | 4.567 |
| 准备加入 | `story_dialog_state_muse_start` | 沉思·起始 | 3.767 |
| 准备加入 | `story_dialog_state_point_end` | 指示手势·收尾 | 2.833 |
| 准备加入 | `story_dialog_state_point_start` | 指示手势·起始 | 3.133 |
| 准备加入 | `story_dialog_state_surprise_end` | 惊讶回应·收尾 | 1.800 |
| 准备加入 | `story_dialog_state_surprise_start` | 惊讶回应·起始 | 1.600 |
| 准备加入 | `story_dialog_virtual_single_idle_talklefthand1` | 左手轻声说明 | 2.833 |
| 准备加入 | `story_dialog_virtual_single_idle_talklefthand2` | 左手展开说明 | 5.733 |
| 准备加入 | `story_dialog_virtual_single_idle_talkrighthand1` | 右手轻声说明 | 2.833 |
| 准备加入 | `story_dialog_virtual_single_idle_talkrighthand2` | 右手展开说明 | 5.733 |
| 准备加入 | `story_dialog_virtual_state_akimbo1_end` | 双手叉腰·收尾 | 2.083 |
| 准备加入 | `story_dialog_virtual_state_akimbo1_loop` | 双手叉腰·循环段 | 4.333 |
| 准备加入 | `story_dialog_virtual_state_akimbo1_start` | 双手叉腰·起始 | 1.333 |
| 准备加入 | `story_dialog_virtual_state_akimboleft_end` | 左手叉腰·收尾 | 3.150 |
| 准备加入 | `story_dialog_virtual_state_akimboleft_loop` | 左手叉腰·循环段 | 4.667 |
| 准备加入 | `story_dialog_virtual_state_akimboleft_start` | 左手叉腰·起始 | 1.933 |
| 准备加入 | `story_dialog_virtual_state_akimboright_end` | 右手叉腰·收尾 | 3.017 |
| 准备加入 | `story_dialog_virtual_state_akimboright_loop` | 右手叉腰·循环段 | 5.350 |
| 准备加入 | `story_dialog_virtual_state_akimboright_start` | 右手叉腰·起始 | 1.383 |
| 准备加入 | `story_dialog_virtual_state_introduction_end` | 介绍自己·收尾 | 1.767 |
| 准备加入 | `story_dialog_virtual_state_introduction_start` | 介绍自己·起始 | 1.367 |
| 准备加入 | `story_dialog_virtual_state_scratchhead_end` | 挠头·收尾 | 2.267 |
| 准备加入 | `story_dialog_virtual_state_think1_end` | 思考·收尾 | 2.200 |
| 准备加入 | `story_dialog_virtual_state_think1_start` | 思考·起始 | 1.700 |
| 备用 | `common_petting_loop` | 主动抚摸候选·循环段 | 10.833 |
| 准备加入 | `common_touchhead_end` | 触头互动候选·收尾 | 2.667 |
| 准备加入 | `common_touchhead_loop` | 触头互动候选·循环段 | 4.000 |
| 准备加入 | `common_touchhead_start` | 触头互动候选·起始 | 4.667 |

## 21个新增表情

| 情绪 | 名字 |
|---|---|
| neutral | `neutral_relax_story` |
| neutral | `neutral_easy_content` |
| neutral | `neutral_soft_attention` |
| happy | `happy_headpat_received` |
| happy | `happy_quiet_pleased` |
| happy | `happy_gentle_smile` |
| shy | `shy_headpat` |
| shy | `shy_bashful_smile` |
| shy | `shy_restrained` |
| thinking | `thinking_puzzle_soft` |
| thinking | `thinking_considering_gently` |
| thinking | `thinking_unsure` |
| sad | `sad_worried_soft` |
| sad | `sad_concerned_listening` |
| sad | `sad_small_uncertainty` |
| surprised | `surprised_mild_notice` |
| surprised | `surprised_warmly_curious` |
| surprised | `surprised_soft_question` |
| affection | `affection_relaxed_nearby` |
| affection | `affection_warm_response` |
| affection | `affection_trusting` |
