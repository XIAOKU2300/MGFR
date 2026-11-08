# 祀蓝白泳装：限定输入复现

## 工具与输入

需要 Python 3.10+、NumPy、SciPy、Pillow；先检查现有环境。渲染另需目标项目兼容的本地 Unity Editor，无需游戏进程或 Blender。缺依赖时使用明确的新环境，遵循宿主安装授权；不要在用户现有环境里盲目升级。

本案例输入为：

- MGFR `si_model.json`、`si_model.bin`、`textures/`，基于祀 PMX 转换。
- 蓝白泳装 Mod 的 `mod.ini`、`Meshes/*.buf`、`Textures/*.dds`。
- `si-profile.json` 的内容指纹用于防止不同资源套用固定绘制区间。哈希仅用于识别，不包含网格或贴图。

从 skill 根目录执行（路径替换为使用者自己的路径）：

```powershell
python scripts/port_si.py inspect --base 'H:\MGFR\converted\si' --mod 'F:\EFMI\Mods\祀\祀-泳装'
python scripts/port_si.py convert --base 'H:\MGFR\converted\si' --mod 'F:\EFMI\Mods\祀\祀-泳装' --out 'H:\MGFR\converted\new-swimsuit-run'
python scripts/port_si.py convert --base 'H:\MGFR\converted\si' --mod 'F:\EFMI\Mods\祀\祀-泳装' --out 'H:\MGFR\converted\new-barefoot-run' --barefoot
```

输出根目录必须不存在。`model/` 是交付模型；`stages/` 是中间结果；`WORKLOG.md`、`source-hashes.json` 记录过程与输入。中间产物不代表视觉验收通过。

## 转换行为

带鞋路径重用已运行过的三个转换步骤：EFMI 解码与绑定 → atlas/UV 修正 → 去掉旧尾部挂饰并恢复 14 材质槽。

赤脚路径接着移除 shoes 绘制组，平放脚掌、重建静止骨架与绑定，再对脚踝局部细分和修整脚背过渡。当前基础脚部渐变已收窄到脚踝下方，避免再次生成被用户否定的小腿 S 弯。

约 13.115° 手臂校正、约 17.995° 平脚校正、828/518 骨骼组数量、原部件绘制范围、0.018 m 脚趾控制点、特定脚踝曲线参数都只属于该输入。前者来自本案例的几何比较，脚踝曲面是修正候选，不是通用人体参数。

## 输入不匹配

inspect/convert 在写输出前检查 profile。拒绝时列出不匹配的结构或文件；不要修改指纹文件来绕过检查。新皮肤应先独立研究、建立对应关系、进行真实渲染，再新增自己的 profile 和转换路径。

## 验证与加载

```powershell
python scripts/model_tool.py inspect 'H:\MGFR\converted\new-barefoot-run\model'
python scripts/model_tool.py verify 'H:\MGFR\converted\new-barefoot-run\model' --base 'H:\MGFR\converted\si'
```

verify 是只读检查，不证明自然度。需要保存结果时使用不存在的 `--report` 路径。

`SiCharacterLoader` 的 `dataRootOverride` 必须在新实例 Build 前设置。已经 Build 的实例因 IsReady 会直接返回，单改目录不能重载。换肤功能由用户实现时，只交付入口与契约，不改宿主。
