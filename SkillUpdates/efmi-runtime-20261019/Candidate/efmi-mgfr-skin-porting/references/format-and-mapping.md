# 数据格式、映射与宿主契约

## EFMI

- `.buf` 是原始顶点/索引缓冲；`.ini` 提供资源路径、步长、索引格式、绘制区间和切换条件；`.dds` 是贴图。它们不是完整 FBX/PMX 骨架。
- 以 INI 中的 `R16_UINT` / `R32_UINT` 判断索引宽度；某资源 `stride=6` 表示一个 16-bit 三角形的字节数，不能误当单索引宽度。
- 本案例 VB0 为 16 字节：前 12 字节 float3 坐标，剩余压缩数据不当作 float 法线。VB1 的实际步长按缓冲/顶点数计算，UV 为前 float2。VB2 为四个 uint16 归一权重，加四个 uint16 骨骼组索引。
- 确认以上布局后才使用。其他组件或版本可不同，不能按扩展名猜格式。
- 区分真正绘制的部件、LOD、切换体型、CPU posed 部件、占位零网格、依赖原游戏的组件和特效；所有存储顶点之和不等于同时可见规模。

## MGFR binary v1

小端 magic `0x5346474D` + uint32 version 1。数量从 JSON counts 读取：

| 顺序 | 类型与数量 |
|---|---|
| positions / normals | 各 float32 × 3 × vertices |
| UV | float32 × 2 × vertices |
| skin indices / weights | uint16 × 4 × vertices；float32 × 4 × vertices |
| triangles | uint32 × indices |
| inverse binds | float32 × 16 × bones，row-major |
| submeshes | uint32 × 2 × materials：indexStart、indexCount |
| 每个 blendShape | uint32 × vertexCount 的顶点索引，再 float32 × 3 × vertexCount 的位移 |

必须检查二进制恰好读完；counts、submesh 连续范围、形变数量与实际数据一致。局部细分后同步权重/UV、索引、形变索引映射和部件范围。

## 坐标与静止姿态

本案例的 EFMI 点转为 `(-x,z,y)`，用与原头发重合的点验证，并用三角形叉积与旧法线判断绕序。不能仅凭“Unity/MMD/Blender 左右手系”口诀决定。

手臂静止角度不同。几何对比得到约 13.115° 的双侧手臂校正；直接最近点转权重会错配手指。先对齐，再建立游戏组到原 PMX 蒙皮权重的对应。对称手指、袖子与身体靠近处尤其要看动作图。拟合不是恢复了源骨骼真名，也不是证明解剖正确。

已有旧 JSON 曾把绝对坐标写入 localScaled，再把它沿父链累加。新模型输出标准父相对坐标；inverse bind 必须由同一绝对静止姿态生成。不能只修顶点而继续用错误 bind，也不能把旧运行时修复分支重复套到已修正数据。

## 材质与 UV

14 个槽的语义：0..6 脸/眼/口；7 身体；8 衣物；9 Cloth2/角；10 透明衣物；11 表情；12 头发；13 发影。新衣物共用 atlas 不代表透明层应合并到不透明层。

本案例：新 DDS 经 Pillow 解码的 PNG 使用翻转 V；沿用原 PMX PNG 的角使用未翻转的游戏 V。匹配点的 UV 比较与真实图片发现了这个差别。不可统一翻转两类 atlas。Component 3 的主尾与蓝白装饰使用新泳装 atlas，不能套原 Cloth1。

`N` 来自 BC5，作为线性法线数据；`L` 的原通道定义未被证明与现有 PackedData 相同，不能直接当金属度/粗糙度输入。不要把原服装 normal/packed/emission 硬套到新泳装。

## 宿主依赖

检查 Loader、IdleMotionPlayer、FaceAttentionController、LegPlantSolver、SkirtDynamics、SiStylizedRenderer 和 SiEndfieldClothing。它们可能按骨骼索引、形变名称或材质槽工作。

本案例保留骨骼名/索引/父子关系和形变名，赤脚版的静止位置发生了必要改变。使用新模型自带的骨架与 bind；不要为“兼容”而恢复高跟鞋静止坐标。现有布料代码存在不等于泳装袖子/裙片已完成独立布料模拟。
