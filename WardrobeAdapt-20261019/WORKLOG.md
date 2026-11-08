# 祀泳装穿脱适配记录 — 2026-10-19

1. **范围确认**：用户选择先做部件拆分、抓取点和接口，记录清楚；本次不接真实手部穿脱，不改现有项目、模型和启动器。
2. **输入核对**：当前 `converted/skins/si-swimsuit-barefoot-ankle-v4`，73,377 顶点；另核对 `si-swimsuit-ready` 带鞋版，68,594 顶点。两版均为 828 骨骼、40 表情、14 材质。源文件指纹见 `source-hashes.json`。
3. **部件映射**：按 conversion-report 的实际来源组及顶点区间选取三角形，按模型左右分开袖片/鞋。赤脚版 8 个部件、15,768 三角形；带鞋版 10 个、18,277 三角形。无交叠、无漏选，不重排顶点、不改 UV/权重/rest/bind/表情。
4. **抓取与穿回**：每部件配置最多 3 个实际表面顶点作为抓取点，保存法线和蒙皮权重；给出拉脱方向/距离及穿回半径/角度。参数属于待头显校准的建议值。
5. **接口实现**：显式 `WardrobeAdapter`，包含指纹验证、逐部件分离/恢复、随骨骼的抓取点、布料控制权交接接口、鞋子姿态接口；无自动场景安装。最终接口在 `Package/Adapter/`。
6. **首轮验证**：全部部件独立往返、组合逆序往返、错误配置拒绝、布料/脚姿态拒绝策略通过；实际查看罩裙分离、饰物隐藏和单鞋分离。发现编辑器 GPU 姿态截图未及时刷新，首轮抬臂图不作为动作验收。
7. **修正验证方式**：第二轮及最终轮每张图先 BakeMesh 当前蒙皮后渲染，已查看抬臂后袖片随骨骼变化的真实图片。抓取点数值也与 BakeMesh 顶点核对。最终轮另缓存抓取点计算所需数组，避免高频查询复制整个模型。
8. **明确限制**：本模型无独立丝袜；泳衣主体保留。带鞋/平脚配置不同，尚未制作连续穿鞋/脱鞋脚部过渡。探针对鞋子只验证几何拆装，未验证姿态协调或 VR。现有 XPBD 布料与手部抓取尚未接入这些接口。
9. **输入保护**：适配后重核对 34 个源文件，全部 hash 不变，见 `source-verification.json`。资源只生成到本目录，未提交或公开发布。

交付入口：`Package/README.md`。结构检查：`structure-checks.json`。最终 Unity 验收结果和真实截图：`ReviewFinal/`；验证命令与运行日志：`probe-final.log`、`scripts/prepare_final_probe.py`。

复现脚本均拒绝已有输出目录。验证命令：

```powershell
H:\MGFR\Editor\Unity.exe -batchmode -noUpm `
  -projectPath H:\MGFR\WardrobeAdapt-20261019\ProbeFinal `
  -executeMethod WardrobeProbe2.Run `
  -wardrobePackage H:\MGFR\WardrobeAdapt-20261019\Package `
  -wardrobeReview <新的截图目录> -logFile <新的日志路径>
```
