# 第三方代码与资源声明

根目录 MIT 许可证只覆盖本项目有权授权的原创部分。第三方代码、游戏 IP、模型、动画、声音、数据和工具继续适用原权利人的条款；本声明不代替原许可，也不扩大任何授权。

## ZMD 参考与派生代码

2026-11-08，项目维护者确认：已获准对所提供的 ZMD 渲染参考工程进行改编，并随本项目再分发源码。本源码候选据此保留相应代码。许可确认记录见 [ZMD_PERMISSION.md](docs/ZMD_PERMISSION.md)。

适用范围包括 `ZMD/Assets/Char/`、`ZMD/Assets/Env/`、`ZMD/Assets/Game_art/`、`ZMD/Assets/Script/`，多个 Unity 工程中的 `RenderStyles/ZmdEndfield/`，以及当前修复工程相应的 ZMD 派生着色器。原作者权利和既有署名继续保留，这些第三方及派生部分不因根目录许可证而自动成为 MIT 代码。

当前记录没有附上游公开发布地址或独立许可全文，因此不据此替原作者承诺无条件商用、任意再许可或对所有使用者授予 MIT 权利。确认只涉及代码，不包括角色模型、贴图、动作、音色以及原工程夹带的商业插件。

## 未随快照提供的商业插件

- **MagicaCloth 2**：本快照不包含 `ZMD/Assets/Plugin/MagicaCloth2/`、对应目录元文件及其旧提交历史。MagicaSoft 官方说明禁止向第三方再分发该资源；需要使用者自行取得适当许可。本项目当前移植记录明确没有安装该插件，也没有改用其衣料物理。
- **Amplify Shader Editor**：参考工程本机副本包含该编辑器插件，但它不在本快照中；原作者允许 ZMD 代码再分发的确认不延伸至该插件。

MagicaSoft 官方说明：<https://magicasoft.jp/en/mc2_about/>。Unity Asset Store 条款：<https://unity.com/legal/as-terms>。

## 保留的第三方声明

- **Unity XR Hands**：保留各 Unity 工程 `Assets/MGFR/Resources/BareHands/Unity-XR-Hands-LICENSE.md` 中的 Unity Package Distribution License 声明。本候选这些目录仅包含声明及其元文件，不提供手部网格、贴图或材质资源。
- **PyYAML**：`SkillUpdates/efmi-runtime-20261019/ValidationDeps/` 中保留的源码副本按其 MIT 许可证使用，原文本位于 `pyyaml-6.0.3.dist-info/licenses/LICENSE`。
- **Unity 及其包**：Unity Editor、引擎和通过 Package Manager 安装的包遵循各自条款。包清单中的依赖声明不表示依赖被本项目重新许可。

## 外部运行依赖

本项目通过依赖声明或本地适配使用 GPT-SoVITS、SenseVoice / sherpa-onnx、Silero VAD、Mem0、Qdrant / FastEmbed 等组件；模型文件还涉及各模型发布方的许可。使用者应核对实际使用版本的上游条款，根目录 MIT 文件不替代这些许可。

## 不随源码提供的资源

本地使用的《明日方舟：终末地》角色、动作、皮肤、贴图、语音权重、参考音频和转换产物不属于本项目 MIT 授权范围，也不随初步源码公开候选提供。相关角色与商标归原权利人所有。

如发现来源缺失或声明错误，请通过仓库问题报告提供具体路径和公开来源依据；请勿上传受限资源、真实配置或私人数据。
