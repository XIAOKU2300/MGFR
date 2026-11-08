# 技能包验证记录（2026-10-19）

使用的是本包内的脚本与新建输出路径，不是只检查原工作目录里的旧脚本。

| 检查 | 实际结果 |
|---|---|
| skill-creator quick_validate | 通过，含 YAML frontmatter 与命名检查 |
| Python 语法与文档相对链接 | 通过 |
| 固定资源 profile | 原输入 98 个文件内容匹配 |
| 完整 convert --barefoot | 五个阶段执行成功，73,377 顶点、92,980 三角形 |
| 新结果与原 v4 候选对比 | 三角形索引相同，bind 相同，最大顶点差约 2.61e-8 m |
| 通用结构验证 | 骨架/形变/材质契约、索引、权重、法线、rest/bind 检查通过 |
| 源文件保护 | 转换前后 98 个输入 hash 不变 |
| 输出已存在 | 写入前拒绝 |
| 输入换成另一泳装包 | profile 不匹配，拒绝且未创建输出 |
| prepare_probe + Unity | 新建隔离项目，Unity 6000.3.26f1 的 BarefootProbe 完成 |
| 真图 | 新跑的脚部侧面、正面已打开检查，复现了 v4 候选 |
| skill 包资源隔离 | 不包含模型、贴图、buf、DDS、渲染图片或密钥 |

Unity 新跑结果：静止蒙皮最大误差 `2.45792e-7 m`，抬臂最大几何变化约 `0.4448 m`，眨眼与口型改变了几何。这些是探针证明的范围，不是自然度或完整动画验收。

本机复核产物位于 `H:\MGFR\converted\skill-validation-20261019-barefoot`、`skill-validation-20261019-probe` 与 `skill-validation-20261019-review`，不随 skill 分享。

用户仍未确认脚踝 v4 的自然度；技能包通过测试不代表该模型获得了用户视觉确认。
