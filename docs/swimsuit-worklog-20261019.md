# 祀泳装适配工作记录

## 范围

- 用户要求：先制作蓝白款祀泳装，简单记录全过程，后续再整理为 skill。
- 最新约束：只交付独立模型文件夹，不替换当前角色，不实现皮肤切换。
- 输入：`F:\EFMI\Mods\祀\祀-泳装`，当前骨架/表情：`H:\MGFR\converted\si`。均只读。
- 输出均使用新路径；不修改已有模型、Unity 项目和启动文件。

## 2026-10-19：格式与策略

1. EFMI 配置定义了部件、三角形绘制区间、DDS 贴图和 16-bit 游戏骨骼权重；不是 FBX/PMX。
2. 保留现有 PMX 的脸、眼睛、口腔、头发和表情，替换身体、衣服、角与尾巴。
3. 保留全部 828 根骨骼的名字、顺序、层级，以及 40 个形变名称。材质 0..13 保持原有语义，尾巴增加材质 14。
4. 坐标对应为 `(-x,z,y)`，UV 的 V 翻转。用原始头发的三角形与现有法线比较，确定三角形绕序。
5. 泳装与 PMX 的手臂静止角度不同。扫描匹配手部得到两侧约 13.115 度，校正后手部最近点距离中位数约 1.5 mm。
6. 身体采用现有皮肤权重的空间对应，拟合游戏骨骼组到 PMX 权重；配饰明确跟随头部。裙摆/袖子先做基础蒙皮，不新建复杂布料模拟。
7. 原始转换数据存在把绝对坐标写入 localScaled 的遗留问题，当前运行时另有补偿。只在新皮肤中输出正确的父节点相对坐标与 inverse bind，避免依赖旧数据修复分支。

## 复现入口

`python tools/skins/build_swimsuit_v1.py --out H:\MGFR\converted\si-swimsuit-20261019-v1`

脚本拒绝已有输出目录。核验、渲染证据和最终接入说明将在完成后追加。


## 2026-10-19：转换、修正、验证与交付

- 初版输出：`converted/si-swimsuit-20261019-v1`。基础检查通过，但真实渲染发现角和原尾部装饰贴图错位，因此没有将初版当成最终结果。
- UV 证据：原始角/头发匹配点的 game V 与现有 PMX 转换后 V 相等；使用原 PNG 的角不可再次翻转 V。泳装 DDS 解码 PNG 使用翻转后的 V。不能给两类贴图统一翻转规则。
- 二版：`finalize_swimsuit_v2.py` 修正原贴图 UV，并把 Component 3 的主尾和配套装饰路由到新的泳装 atlas。
- 三版：`package_swimsuit_v3.py` 保留主尾和蓝白装饰，省略两个依赖游戏原贴图的旧机械挂饰部件，压紧未引用顶点，恢复与当前模型完全一致的 14 材质槽。
- Unity 最小验证项目首次启动遇到 Package Manager IPC 限制；隔离运行后又遇到 `path argument ... undefined`。无需安装依赖，最终使用 `-noUpm` 和现有 Unity 模块完成验证。隔离项目为 `converted/swimsuit-probe-project-v2`，没有向工作 Unity 项目添加文件。
- 最终实测：Unity 6000.3.26f1，68,594 顶点，80,405 三角形，828 骨骼，40 形变，14 材质。静止蒙皮最大误差 3.579382e-7 m；抬臂使网格实际移动最大 0.4447745 m；眨眼+口型使网格实际移动。数字仅证明对应检查，不代替穿模/实机验证。
- 实际查看了正面、背面、斜面、抬臂、抬腿、眨眼口型图片，修正了实际截图中发现的 atlas 问题。截图使用基础 MGFR 材质，不是完整项目风格化渲染。
- `verify_swimsuit.py` 的 14 项数据检查全部通过：骨骼/父子关系、形变、材质槽与原模型一致；源文件 hash 未变；顶点/索引/法线/权重/贴图/形变范围及 rest-bind 合法。
- 最终交付：`H:\MGFR\converted\skins\si-swimsuit-ready`，模型原生 bin/json、PNG、skin.json、使用说明、转换报告、检查结果和 review 图片。
- 没有替换 `converted/si`、`Assets/StreamingAssets/si`，没有接入皮肤切换，没有改启动器，没有提交或发布模型资产。
- 未完成/范围外：正式 VR 会话、完整 idle/交互集成、独立泳装布料模拟、风格化渲染器按皮肤选择贴图。后续模型不得把离线验证写成这些项目已经完成。

## 复现完整交付

所有输出目录必须不存在。路径可自行改成新目录：

```powershell
python tools/skins/build_swimsuit_v1.py --out H:\MGFR\converted\si-swimsuit-20261019-v1
python tools/skins/finalize_swimsuit_v2.py --input H:\MGFR\converted\si-swimsuit-20261019-v1 --out H:\MGFR\converted\skins\si-swimsuit
python tools/skins/package_swimsuit_v3.py --input H:\MGFR\converted\skins\si-swimsuit --out H:\MGFR\converted\skins\si-swimsuit-ready
python tools/skins/verify_swimsuit.py H:\MGFR\converted\skins\si-swimsuit-ready
```

验证渲染入口：`tools/skins/SwimsuitProbe.cs`（在隔离 Unity 项目中运行 `SwimsuitProbe.Run`，参数 `-skinRoot <模型目录> -probeDir <不存在的截图目录>`；命令带 `-batchmode -noUpm`）。

后续整理 skill 时保留：源资源只读、输出新路径、依据 INI draw range 选择部件、对齐 rest pose、按 atlas 验证 UV、保留骨骼和形变契约、必须看真实渲染、区分离线验证与实机验证。不要复制个人模型贴图进 skill。


## 2026-10-19：用户追加赤脚与平脚姿态

- 用户要求去掉鞋子，并明确脚不能保持高跟鞋踮脚形态。继续采用独立文件夹，不替换已有模型。
- 输入为已验收的 `converted/skins/si-swimsuit-ready`；输出为 `converted/skins/si-swimsuit-barefoot-ready`。
- `make_barefoot_swimsuit.py` 精确移除 shoes 部件的 2,931 顶点/2,509 三角形（包含鞋底、鞋跟和绑带），其他衣物保留。
- 以实际皮肤脚底网格的脚跟/前脚掌接触高度为目标，用一维求根得到两侧约 17.995° 的脚踝旋转。脚踝以上 0.16..0.28 m 用 smoothstep 混合，避免直接旋转整段小腿。
- 全身和静止骨架下移约 0.062833 m；更新脚踝、脚趾/IK 目标并重建 bind poses。脚趾控制点保持在地面上方 0.018 m，避免沿用旧高跟鞋静止坐标使它落入地下。
- 第一轮真实脚部近景确认脚跟已放下，但发现脚踝 UV 接缝处法线断层；`finish_barefoot_skin.py` 将重合位置的皮肤顶点共享面积加权法线，没有焊接 UV 或改变几何拓扑。
- 最终检查：65,663 顶点、77,896 三角形、828 骨骼、40 形变、14 材质；左右脚跟/前脚掌距地约 0.441 mm，无几何低于地面。骨骼名称/顺序/父子关系与原泳装相同，静止位置为赤脚重算。
- Unity 6000.3.26f1 隔离渲染包含脚部侧面、正面、双脚斜面、全身及基础动作/口型。静止蒙皮最大误差 2.45792e-7 m；真实查看近景确认自然足弓与脚趾保留，脚跟没有继续抬起。
- 14 项数据核验通过；原泳装 bin/json 与原来源 hash 均未变。没有在正式项目/VR 中切换模型。

复现（输出目录必须不存在）：

```powershell
python tools/skins/make_barefoot_swimsuit.py --input H:\MGFR\converted\skins\si-swimsuit-ready --out H:\MGFR\converted\skins\si-swimsuit-barefoot
python tools/skins/finish_barefoot_skin.py --input H:\MGFR\converted\skins\si-swimsuit-barefoot --out H:\MGFR\converted\skins\si-swimsuit-barefoot-ready
```

渲染入口：`BarefootProbe.Run`，沿用隔离 Unity 项目与 `-batchmode -noUpm`，新增脚部近景。后续 skill 应强调：隐藏鞋子不等于赤脚姿态正确，必须同时检查脚底、脚踝、小腿过渡、静止骨架、bind pose、IK 目标，以及真实侧面截图。


## 2026-10-19：脚踝视觉验收失败后的修正

- 用户指出已交付赤脚版脚踝弯折，随后又指出收窄变形范围后仍不自然。此前“自然过渡已确认”的结论撤回；接地通过不等于视觉通过。
- 诊断：最早的 0.16..0.28 m 旋转混合带动脚踝上方小腿，使其 Z 方向出现约 1 cm 鼓起，形成 S 形弯曲。
- v2：恢复原小腿形状，改为 0.09..0.155 m 内渐变平脚。消除了小腿鼓起，但脚背向小腿的转角仍硬，用户未接受。
- v3：局部一致细分，按截面修整前侧轮廓并收窄跟腱；真实截图发现后侧跟腱收窄过度产生新凹折，放弃。
- v4：保留原后侧轮廓，只修整前侧脚背过渡并温和曲面平滑。已实际查看侧面、正面和斜面近景。用户尚未确认该版自然度，不标记为用户已验收。
- 新路径：converted/skins/si-swimsuit-barefoot-ankle-v4，73,377 顶点/92,980 三角形。足部接地、蒙皮、形变检查通过；距地 20 cm 以上的小腿原有顶点未改形。
- 工具：repair_barefoot_ankle.py；sculpt_barefoot_ankle_v4.py；BarefootProbe.cs。全部新路径，未覆盖旧版或当前项目角色。
- 后续 skill 必须保留失败教训：隐藏鞋子、脚底平放、权重合法、重算法线，都不能代替脚踝自然度。要检查小腿中心线、前后轮廓、关节转角和真实多角度近景。用户否定的版本不能写成成功经验。


## 2026-10-19：完整 skill 生成与验证

- 用户要求生成完整 skill。使用 skill-creator，制作 efmi-mgfr-skin-porting，包含流程、格式/绑定契约、脚踝失败教训、Unity 探针、过程/交付规范、限定输入 profile 和可移植脚本。
- 原受保护的绝对输入路径改为显式参数；带鞋与赤脚基础步骤复用已验证代码，赤脚基础渐变改为脚踝下方，避免再默认复现早期 S 弯。固定部件表仅允许原输入指纹，不冒充通用转换器。
- 包内脚本实际复跑 --barefoot 成功。与原 v4 几何最大差约 2.61e-8 m，三角形索引和 bind 一致；98 个输入 hash 未变。已有输出与另一皮肤输入均被拒绝且未产生误写。
- 用包内 prepare_probe 和探针新建隔离 Unity 项目，重新完成渲染与动作/形变检查，打开新脚部近景查看；结构验证与 skill-creator quick_validate 通过。脚踝 v4 仍未获得用户视觉确认，此状态写入技能包。
- 分享包：SkillDelivery-20261019/efmi-mgfr-skin-porting.zip，共 20 个说明/脚本/profile 文件，不含模型、贴图或密钥。已校验 ZIP 与文件内容。
- 新目录安装并逐文件校验：C:/Users/19829/.codex/skills/efmi-mgfr-skin-porting。没有替换任何已有 skill、当前角色或模型资源。
