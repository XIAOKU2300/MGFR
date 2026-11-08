using System;
using System.IO;
using System.Linq;
using System.Text;
using MGFR.Character;
using UnityEditor;
using UnityEngine;

namespace MGFR.EditorTools
{
    /// <summary>
    /// Builds the character outside play mode and reports what came out, then
    /// renders it.
    ///
    /// This exists because "the character displays on the PC" is the one claim in
    /// this milestone that cannot be checked by reading code. It runs in batch mode
    /// with graphics enabled, so the PNGs it writes are real renders through the
    /// real shader - not a mesh dump, not a description of a mesh dump.
    ///
    /// Run it with:
    ///   Unity.exe -batchmode -quit -projectPath &lt;project&gt; -logFile &lt;log&gt;
    ///             -executeMethod MGFR.EditorTools.CharacterProbe.Run
    /// Do not add -nographics: without a graphics device there is nothing to render
    /// into and the images are skipped (the text report still gets written).
    /// </summary>
    public static class CharacterProbe
    {
        const string OutputFolder = "H:/MGFR/batch";
        const string ShaderName = "MGFR/Character";

        static readonly string[] RequiredBlendShapes = { "まばたき", "あ", "い", "う", "え", "お", "ん" };

        [MenuItem("MGFR/Run Character Probe", priority = 40)]
        public static void Run()
        {
            var report = new StringBuilder();
            var failures = 0;

            report.AppendLine("MGFR character probe");
            report.AppendLine($"  unity      : {Application.unityVersion}");
            report.AppendLine($"  graphics   : {SystemInfo.graphicsDeviceType} / {SystemInfo.graphicsDeviceName}");
            report.AppendLine($"  pipeline   : {(UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline == null ? "Built-in" : "SRP asset assigned")}");
            report.AppendLine();

            GameObject root = null;

            try
            {
                var shader = Shader.Find(ShaderName);
                report.AppendLine($"  shader {ShaderName}: {(shader == null ? "NOT FOUND" : "found")}");
                // A shader that resolves but did not compile still returns from
                // Shader.Find, and the material then draws with Unity's magenta
                // error shader. The render looks like a solid-coloured silhouette
                // and the console stays quiet, so it is worth stating outright.
                if (shader != null)
                    report.AppendLine($"  shader supported: {(shader.isSupported ? "yes" : "NO - it will draw magenta")}");
                if (shader == null)
                {
                    failures++;
                    report.AppendLine("    A shader that is not in the build is a build-only failure:");
                    report.AppendLine("    Shader.Find resolves in the editor from the AssetDatabase, but in a");
                    report.AppendLine("    player it only finds shaders that are included. Add it under");
                    report.AppendLine("    Project Settings > Graphics > Always Included Shaders.");
                }

                root = new GameObject("Character Probe");

                var loader = root.AddComponent<SiCharacterLoader>();
                loader.buildOnStart = false;
                loader.logMaterialTable = false;
                loader.Build();

                report.AppendLine();
                report.AppendLine("  --- build ---");
                report.AppendLine($"  ready      : {loader.IsReady}");
                report.AppendLine($"  status     : {loader.Status}");

                if (!loader.IsReady)
                {
                    failures++;
                    report.AppendLine("  the character did not build; nothing further can be checked.");
                    Write(report, failures);
                    return;
                }

                report.AppendLine($"  build time : {loader.BuildSeconds:F2} s");

                var data = loader.Data;
                report.AppendLine();
                report.AppendLine("  --- geometry ---");
                report.AppendLine($"  vertices   : {data.counts.vertices:N0}");
                report.AppendLine($"  indices    : {data.counts.indices:N0}  ({data.counts.indices / 3:N0} triangles)");
                report.AppendLine($"  bones      : {data.counts.bones:N0}");
                report.AppendLine($"  materials  : {data.counts.materials:N0}");
                report.AppendLine($"  textures   : {data.counts.textures:N0}");
                report.AppendLine($"  morphs     : {data.counts.blendShapes:N0} vertex, {data.counts.materialMorphs:N0} material");

                // The index count decides whether the mesh can use 16-bit indices.
                // Over 65,535 it silently truncates, so it is worth stating.
                var indexFormat = loader.Renderer != null ? loader.Renderer.sharedMesh.indexFormat.ToString() : "(no mesh)";
                report.AppendLine($"  index fmt  : {indexFormat}  (UInt32 required above 65,535 indices)");
                if (data.counts.indices > 65535 && indexFormat != "UInt32")
                {
                    failures++;
                    report.AppendLine("    FAIL: more than 65,535 indices on a 16-bit mesh.");
                }

                report.AppendLine();
                report.AppendLine("  --- size ---");
                var bounds = loader.LocalBounds;
                report.AppendLine($"  local bounds : {Format(bounds.min)} .. {Format(bounds.max)}");
                report.AppendLine($"  height       : {bounds.size.y:F3} m   (source was 22.410 PMX units x 0.08)");
                report.AppendLine($"  width/depth  : {bounds.size.x:F3} x {bounds.size.z:F3} m");

                // Feet at y=0 is what lets SiCharacterController place the root at
                // the ground height and have the feet land on the ground.
                var feetOk = Mathf.Abs(bounds.min.y) < 0.02f;
                report.AppendLine($"  feet at y=0  : {(feetOk ? "yes" : "NO - " + bounds.min.y.ToString("F3") + ", placement will be off by that much")}");
                if (!feetOk)
                    failures++;

                var heightOk = bounds.size.y > 1.4f && bounds.size.y < 2.2f;
                report.AppendLine($"  plausible    : {(heightOk ? "yes" : "NO - expected roughly 1.8 m for an adult model")}");
                if (!heightOk)
                    failures++;

                // Normals are read as raw floats out of the binary, so a stride
                // mistake or a wrong section offset leaves them plausible-looking
                // but not unit length - and the shading then goes wrong in a way
                // that is easy to blame on the light.
                var normals = loader.Renderer.sharedMesh.normals;
                var badNormals = 0;
                var minLength = float.MaxValue;
                var maxLength = 0f;
                foreach (var normal in normals)
                {
                    var length = normal.magnitude;
                    if (length < minLength) minLength = length;
                    if (length > maxLength) maxLength = length;
                    if (Mathf.Abs(length - 1f) > 0.01f) badNormals++;
                }

                report.AppendLine($"  normals      : {normals.Length:N0} unit-length ({minLength:F4}..{maxLength:F4}), "
                                + $"{badNormals:N0} off by more than 0.01");
                if (badNormals > 0)
                    failures++;

                report.AppendLine();
                report.AppendLine("  --- blend shapes ---");
                report.AppendLine($"  count        : {loader.BlendShapeCount}");
                report.AppendLine($"  on the mesh  : {loader.Renderer.sharedMesh.blendShapeCount}  (the count Unity will actually blend)");
                foreach (var shape in data.blendShapes)
                {
                    report.AppendLine($"    [{shape.index,3}] {shape.name,-16} {shape.classification,-12} {shape.vertexCount,6} verts");
                }

                foreach (var required in RequiredBlendShapes)
                {
                    var index = loader.FindBlendShape(required);
                    if (index < 0)
                    {
                        failures++;
                        report.AppendLine($"  MISSING required shape: {required}");
                        continue;
                    }

                    // A shape can have a name, an index and a plausible vertex
                    // count and still be inert. Two separate things have to hold:
                    // the frame has to carry non-zero vertex deltas, and the weight
                    // has to actually reach the renderer. Measuring both is the
                    // only way to tell them apart - a face that never moves looks
                    // the same either way.
                    var maxDelta = 0f;
                    try
                    {
                        var count = data.counts.vertices;
                        var deltaVertices = new Vector3[count];
                        var deltaNormals = new Vector3[count];
                        var deltaTangents = new Vector3[count];
                        loader.Renderer.sharedMesh.GetBlendShapeFrameVertices(index, 0, deltaVertices, deltaNormals, deltaTangents);
                        foreach (var delta in deltaVertices)
                        {
                            var magnitude = delta.magnitude;
                            if (magnitude > maxDelta) maxDelta = magnitude;
                        }
                    }
                    catch (Exception e)
                    {
                        report.AppendLine($"      could not read frame deltas: {e.GetType().Name}: {e.Message}");
                    }

                    loader.SetBlendShape(index, 100f);
                    var readBack = loader.GetBlendShape(index);
                    loader.SetBlendShape(index, 0f);

                    report.AppendLine($"    {required,-8} index {index,3}  largest vertex delta {maxDelta:F4} m  weight read-back {readBack:F0}");

                    if (maxDelta <= 0.0001f)
                    {
                        failures++;
                        report.AppendLine($"      FAIL: {required} moves no vertices, so setting it cannot change the face.");
                    }
                    if (Mathf.Abs(readBack - 100f) > 0.5f)
                    {
                        failures++;
                        report.AppendLine($"      FAIL: {required} was set to 100 but the renderer reports {readBack:F0}.");
                    }
                }

                report.AppendLine();
                report.AppendLine("  --- material morphs (not blend shapes) ---");
                foreach (var morph in data.materialMorphs)
                {
                    report.AppendLine($"    [{morph.index,3}] {morph.name,-16} {morph.classification,-12} {morph.offsets.Length} offsets");
                }
                report.AppendLine($"  blush target material index: {loader.BlushMaterialIndex}");

                report.AppendLine();
                report.AppendLine("  --- physics ---");
                report.AppendLine("  none imported: the converter reads vertices, materials, bones and morphs");
                report.AppendLine("  only. No PMX rigid body or joint is read, so there is no MMD physics to");
                report.AppendLine("  disable and no bone was removed.");

                report.AppendLine();
                report.AppendLine("  --- materials ---");
                foreach (var material in loader.Materials)
                {
                    var mesh = loader.Renderer.sharedMesh;
                    report.AppendLine($"    {material.name,-12} queue {material.renderQueue,5}  zwrite {material.GetInt("_ZWrite")}  "
                                    + $"cull {material.GetInt("_Cull")}  blend {material.GetInt("_SrcBlend")}/{material.GetInt("_DstBlend")}  "
                                    + $"tex {(material.mainTexture == null ? "(none)" : material.mainTexture.width + "x" + material.mainTexture.height)}  "
                                    + $"shader {material.shader.name}{(material.shader.isSupported ? "" : " NOT SUPPORTED")}");
                }

                // "Every material has a texture" is the wrong question. 04_目影 is
                // eye shadow: the PMX genuinely declares texture -1 for it, because
                // it is a flat tint drawn over the eye rather than an image. The
                // question that actually matters is whether every material that
                // asked for a texture got one, since a failed lookup is silent and
                // shows up as a white or magenta surface.
                var declaredNone = data.materials.Count(m => m.texture < 0);
                var unresolved = 0;
                for (var i = 0; i < data.materials.Length && i < loader.Materials.Length; i++)
                {
                    if (data.materials[i].texture < 0)
                        continue;

                    if (loader.Materials[i].mainTexture == null)
                    {
                        unresolved++;
                        report.AppendLine($"  FAIL: {data.materials[i].name} declares texture {data.materials[i].texture} but loaded none.");
                    }
                }

                report.AppendLine($"  no texture declared by the PMX: {declaredNone}   unresolved lookups: {unresolved}");
                if (unresolved > 0)
                    failures++;

                report.AppendLine();
                report.AppendLine("  --- texture mapping ---");
                foreach (var texture in data.textures)
                {
                    report.AppendLine($"    [{texture.index,2}] {texture.route,-22} {texture.file}  ({texture.bytes:N0} B)");
                }

                report.AppendLine();
                report.AppendLine("  --- bones ---");
                var roots = data.bones.Count(b => b.parent < 0);
                var ik = data.bones.Count(b => b.isIk);
                report.AppendLine($"  root bones   : {roots}  (IK bones: {ik})");
                report.AppendLine($"  bones root   : {(loader.BonesRoot == null ? "MISSING" : loader.BonesRoot.name + " with " + loader.BonesRoot.childCount + " children")}");
                if (loader.BonesRoot == null)
                    failures++;

                // A skinned mesh with fewer bones on the renderer than the model has
                // deforms wrongly and usually invisibly, so it is worth asserting.
                var rendererBones = loader.Renderer.bones != null ? loader.Renderer.bones.Length : 0;
                report.AppendLine($"  renderer bones: {rendererBones}");
                if (rendererBones != data.counts.bones)
                {
                    failures++;
                    report.AppendLine($"  FAIL: renderer has {rendererBones} bones, the model has {data.counts.bones}.");
                }

                report.AppendLine();
                report.AppendLine("  --- skinning ---");
                // Baking the mesh applies the bone transforms and the bind poses for
                // real. If the bind poses are wrong the vertices land somewhere
                // unrelated to the model, and this is what shows it: the render is
                // only a green frame, which does not say whether the mesh is missing,
                // deformed, or simply off-screen.
                var baked = new Mesh();
                try
                {
                    loader.Renderer.BakeMesh(baked, true);
                    var bakedBounds = baked.bounds;
                    report.AppendLine($"  baked bounds : {Format(bakedBounds.min)} .. {Format(bakedBounds.max)}");
                    report.AppendLine($"  baked size   : {bakedBounds.size.x:F3} x {bakedBounds.size.y:F3} x {bakedBounds.size.z:F3} m");

                    var original = loader.LocalBounds;
                    var centreDrift = (bakedBounds.center - original.center).magnitude;
                    report.AppendLine($"  centre drift : {centreDrift:F3} m");

                    if (centreDrift > 0.05f || bakedBounds.size.magnitude > original.size.magnitude * 1.5f)
                    {
                        failures++;
                        report.AppendLine("  FAIL: the skinned mesh does not sit where the unskinned mesh does.");
                        report.AppendLine("        The usual cause is a transposed inverse bind matrix:");
                        report.AppendLine("        Unity's Matrix4x4(a,b,c,d) constructor takes columns, so a");
                        report.AppendLine("        row-major stream fed to it comes out transposed.");
                    }
                }
                catch (Exception e)
                {
                    report.AppendLine($"  bake failed: {e.GetType().Name}: {e.Message}");
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(baked);
                }

                report.AppendLine();
                report.AppendLine("  --- blend shape deformation ---");
                // Holding 40 frames with real deltas is not the same as Unity
                // folding them into the skinned result. Those are two separate
                // steps, and only the second one changes what is drawn, so this
                // measures the geometry rather than trusting the weight read-back.
                var deformIndex = loader.FindBlendShape("あ");
                if (deformIndex < 0)
                {
                    report.AppendLine("  skipped: no あ shape to drive.");
                }
                else
                {
                    var neutralMesh = new Mesh();
                    var openMesh = new Mesh();
                    try
                    {
                        loader.SetBlendShape(deformIndex, 0f);
                        loader.Renderer.BakeMesh(neutralMesh, true);
                        loader.SetBlendShape(deformIndex, 100f);
                        loader.Renderer.BakeMesh(openMesh, true);

                        var before = neutralMesh.vertices;
                        var after = openMesh.vertices;
                        var moved = 0;
                        var largest = 0f;
                        if (before.Length == after.Length)
                        {
                            for (var i = 0; i < before.Length; i++)
                            {
                                var distance = (after[i] - before[i]).magnitude;
                                if (distance > 0.0001f) moved++;
                                if (distance > largest) largest = distance;
                            }
                        }

                        report.AppendLine($"  あ at 100 moves {moved:N0} of {before.Length:N0} baked vertices, largest {largest:F4} m");
                        if (moved == 0)
                        {
                            failures++;
                            report.AppendLine("  FAIL: the weight reaches the renderer but moves no geometry.");
                            report.AppendLine("        Either the frames are inert or BakeMesh ignores blend shapes;");
                            report.AppendLine("        the frame-delta measurement above distinguishes the two.");
                        }
                    }
                    finally
                    {
                        loader.SetBlendShape(deformIndex, 0f);
                        UnityEngine.Object.DestroyImmediate(neutralMesh);
                        UnityEngine.Object.DestroyImmediate(openMesh);
                    }
                }

                report.AppendLine();
                report.AppendLine("  --- render ---");
                failures += Render(root, loader, report);
            }
            catch (Exception e)
            {
                failures++;
                report.AppendLine();
                report.AppendLine($"EXCEPTION: {e}");
            }
            finally
            {
                if (root != null)
                    UnityEngine.Object.DestroyImmediate(root);
            }

            Write(report, failures);
        }

        /// <summary>
        /// Renders three views: the whole figure, the head, and the head with the
        /// blink and mouth morphs driven, so the last one proves the morphs move
        /// geometry rather than merely existing in a list.
        /// </summary>
        static int Render(GameObject root, SiCharacterLoader loader, StringBuilder report)
        {
            var failures = 0;

            if (SystemInfo.graphicsDeviceType == UnityEngine.Rendering.GraphicsDeviceType.Null)
            {
                report.AppendLine("  skipped: no graphics device (-nographics). Re-run without it.");
                return failures;
            }

            var camGo = new GameObject("Probe Camera");
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            // The same key green the scene uses, so the render is representative of
            // what ALVR will key out.
            cam.backgroundColor = new Color(0f, 1f, 0f, 1f);
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 20f;
            cam.allowHDR = false;
            cam.allowMSAA = false;
            cam.fieldOfView = 35f;

            var lightGo = new GameObject("Probe Light");
            lightGo.transform.rotation = Quaternion.Euler(35f, -25f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.1f;
            light.shadows = LightShadows.None;

            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.42f, 0.42f, 0.46f);

            Directory.CreateDirectory(OutputFolder);

            Shoot(cam, new Vector3(0f, 0.95f, -2.6f), new Vector3(0f, 0.9f, 0f), 900, 1400, "si-01-fullbody.png", report);
            var neutral = Shoot(cam, new Vector3(0f, 1.58f, -0.75f), new Vector3(0f, 1.56f, 0f), 800, 800, "si-02-head.png", report);

            var blink = loader.FindBlendShape("まばたき");
            var mouth = loader.FindBlendShape("あ");
            if (blink >= 0) loader.SetBlendShape(blink, 100f);
            if (mouth >= 0) loader.SetBlendShape(mouth, 70f);

            // A weight change on its own does not make a batch run re-evaluate the
            // skinned mesh. BakeMesh reports the new geometry straight away while
            // the drawn image stays byte-identical, which is the signature of a
            // cached evaluation rather than of a weight that never arrived.
            // Toggling the renderer off and on is the cheapest way to make Unity
            // drop that cache, and updateWhenOffscreen stops the bounds it cached
            // before the morph from deciding whether the renderer is updated.
            var skinned = loader.Renderer;
            skinned.updateWhenOffscreen = true;
            skinned.enabled = false;
            skinned.enabled = true;

            var morphed = Shoot(cam, new Vector3(0f, 1.58f, -0.75f), new Vector3(0f, 1.56f, 0f), 800, 800, "si-03-blink-mouth.png", report);
            if (blink >= 0) loader.SetBlendShape(blink, 0f);
            if (mouth >= 0) loader.SetBlendShape(mouth, 0f);

            // The two head shots share a camera and differ only in the weights, so
            // identical bytes mean the morphs never reached the image at all. The
            // probe checks that itself rather than leaving it to whoever looks at
            // the pictures, because two green-and-skin frames are easy to mistake
            // for one another by eye.
            if (Same(neutral, morphed))
            {
                failures++;
                report.AppendLine("  FAIL: the blink and mouth shot is byte-identical to the neutral one.");
            }
            else
            {
                report.AppendLine("  the blink and mouth shot differs from the neutral one, as it must.");
            }

            // Insurance. Whether or not the renderer's own draw picked the weights
            // up, the baked mesh is the geometry that draw is supposed to produce,
            // and BakeMesh demonstrably applies both the skinning and the blend
            // shapes. So if the two shots above came out identical, this is the
            // picture of the morph to read instead.
            byte[] bakedShot = null;
            var bakedMesh = new Mesh();
            GameObject bakedGo = null;
            try
            {
                if (blink >= 0) loader.SetBlendShape(blink, 100f);
                if (mouth >= 0) loader.SetBlendShape(mouth, 70f);

                loader.Renderer.BakeMesh(bakedMesh, false);

                bakedGo = new GameObject("Probe Baked Morph");
                bakedGo.transform.SetPositionAndRotation(skinned.transform.position, skinned.transform.rotation);
                bakedGo.transform.localScale = skinned.transform.lossyScale;
                bakedGo.AddComponent<MeshFilter>().sharedMesh = bakedMesh;
                bakedGo.AddComponent<MeshRenderer>().sharedMaterials = loader.Materials;

                // Hide the skinned draw, or the two copies overlap and the thing
                // this shot exists to show is buried under the un-morphed one.
                skinned.enabled = false;
                bakedShot = Shoot(cam, new Vector3(0f, 1.58f, -0.75f), new Vector3(0f, 1.56f, 0f), 800, 800, "si-04-morph-baked.png", report);
            }
            finally
            {
                skinned.enabled = true;
                if (blink >= 0) loader.SetBlendShape(blink, 0f);
                if (mouth >= 0) loader.SetBlendShape(mouth, 0f);
                if (bakedGo != null) UnityEngine.Object.DestroyImmediate(bakedGo);
                UnityEngine.Object.DestroyImmediate(bakedMesh);
            }

            report.AppendLine(Same(neutral, bakedShot)
                ? "  NOTE: even the baked mesh shot matches the neutral one, so the morph does not reach the geometry."
                : "  the baked mesh shot differs from the neutral one, so the morph does move the geometry.");

            UnityEngine.Object.DestroyImmediate(lightGo);
            UnityEngine.Object.DestroyImmediate(camGo);

            return failures;
        }

        static byte[] Shoot(Camera cam, Vector3 position, Vector3 lookAt, int width, int height, string fileName, StringBuilder report)
        {
            var path = Path.Combine(OutputFolder, fileName).Replace('\\', '/');

            var renderTexture = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32);
            renderTexture.Create();

            var previous = RenderTexture.active;
            cam.transform.position = position;
            cam.transform.LookAt(lookAt);
            cam.targetTexture = renderTexture;

            // Twice. A -executeMethod batch run has no player loop, so the skinned
            // mesh is evaluated on demand and the result is reused; a blend shape
            // weight changed since that evaluation can still be missing from the
            // first image. The second pass is the one kept.
            cam.Render();
            cam.Render();

            RenderTexture.active = renderTexture;
            var texture = new Texture2D(width, height, TextureFormat.RGB24, false);
            texture.ReadPixels(new Rect(0f, 0f, width, height), 0, 0);
            texture.Apply();

            RenderTexture.active = previous;
            cam.targetTexture = null;

            var png = texture.EncodeToPNG();
            File.WriteAllBytes(path, png);

            UnityEngine.Object.DestroyImmediate(texture);
            renderTexture.Release();
            UnityEngine.Object.DestroyImmediate(renderTexture);

            report.AppendLine($"  wrote {path}  ({png.Length:N0} B, {width}x{height})");
            return png;
        }

        static string Format(Vector3 v) => $"({v.x:F3}, {v.y:F3}, {v.z:F3})";

        static bool Same(byte[] a, byte[] b)
        {
            if (a == null || b == null || a.Length != b.Length) return false;
            for (var i = 0; i < a.Length; i++)
            {
                if (a[i] != b[i]) return false;
            }

            return true;
        }

        static void Write(StringBuilder report, int failures)
        {
            report.AppendLine();
            report.AppendLine(failures == 0 ? "RESULT: pass" : $"RESULT: {failures} problem(s)");

            var text = report.ToString();
            Debug.Log("[CharacterProbe]\n" + text);

            try
            {
                Directory.CreateDirectory(OutputFolder);
                File.WriteAllText(Path.Combine(OutputFolder, "character-probe.txt"), text, new UTF8Encoding(false));
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[CharacterProbe] could not write the report file: {e.Message}");
            }
        }
    }
}
