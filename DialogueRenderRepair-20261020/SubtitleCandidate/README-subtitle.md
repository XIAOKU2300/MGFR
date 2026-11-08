字幕栏绿底修复候选（未覆盖现有程序）

根因：实际 CameraChatOverlay 使用 alpha=.89 的暗色背板及字体 atlas，ChatOverlay.shader 的 SrcAlpha 混合把背后的纯绿混进字幕底色。ALVR RGB key 随后无法识别这些混合色。

最终集成源：Runtime-v2/ChatOverlayChroma.shader 和 Runtime-v2/SubtitleChromaRepair.cs。

集成：载入 shader asset bundle 后调用 MGFR.Repairs.SubtitleChromaRepair.Install(shader)。资源名可由宿主自行确定，Shader 名为 MGFR/ChatOverlayChroma。Install 不依赖 bundle 路径。组件拥有 Camera.onPreRender / onPostRender 的全局 _MGFRRgbKeyCoverage 设置和栈恢复，衣服 shader 可共用该全局。全局 _MGFRRgbKeyCoverageCell 由宿主初始化。

Key camera 下把字幕背板变为不透明中性色，字体仍在其上正常抗锯齿混合，避免细网点与 YUV420 再混绿。非 key camera 保持原透明度与原逐像素外观。既有 Material 实例、atlas 更新、队列、字幕内容和可见性保留。父模块须确保 key-camera MSAA 关闭；原 MrChromaEdgeGuard 的 XR/force 条件应满足。

PixelProbe-v2/result.json 是使用真实 CameraChatOverlay 源码、真实微软雅黑 atlas 的独立桌面渲染结果：旧41,319个残绿像素，新0；非key逐像素差0。已打开输出图片确认。

Yuv420Probe-v1/result.json 是 BT709 2x2 chroma box subsampling、8bit量化重建模拟。早期1px细Bayer字幕内部18,505/40,960像素混绿；最终中性实底0/40,960。不是实际编码器、ALVR或头显验收。早期v1文件保留用于反例，不应集成。
