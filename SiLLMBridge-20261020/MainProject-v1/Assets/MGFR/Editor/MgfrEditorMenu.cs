using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Microsoft.Win32;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.Rendering;

namespace MGFR.EditorTools
{
    /// <summary>
    /// The editor side of milestone ①: set the project up, make an (empty) scene,
    /// and report what is actually configured.
    ///
    /// "Check Setup" is the one to run first and after every change. It reads the
    /// live values rather than assuming the menu items below were ever run.
    /// </summary>
    public static class MgfrEditorMenu
    {
        const string MenuRoot = "MGFR/";
        const string SceneFolder = "Assets/MGFR/Scenes";
        const string ScenePath = SceneFolder + "/SmokeTest.unity";
        const string CharacterScenePath = SceneFolder + "/SiCharacter.unity";
        const string OpenXrLoaderTypeName = "UnityEngine.XR.OpenXR.OpenXRLoader";
        const string OpenXrRegistryPath = @"SOFTWARE\Khronos\OpenXR\1";

        /// <summary>
        /// Created at runtime by <c>SiCharacterLoader</c>, so nothing in the project
        /// references it and the build would otherwise leave it out.
        /// </summary>
        const string CharacterShaderName = "MGFR/Character";

        /// <summary>
        /// Where <c>tools/pmx/convert_si.py</c> writes. Overridable through the
        /// <c>MGFR.ConvertedPath</c> editor preference so a checkout somewhere else
        /// does not need this file edited.
        /// </summary>
        const string ConvertedPathPrefKey = "MGFR.ConvertedPath";
        const string DefaultConvertedPath = "H:/MGFR/converted/si";

        static string ConvertedPath =>
            EditorPrefs.GetString(ConvertedPathPrefKey, DefaultConvertedPath);

        // ---- Check ----------------------------------------------------------

        [MenuItem(MenuRoot + "Check Setup", priority = 10)]
        public static void CheckSetup()
        {
            var report = new StringBuilder();
            report.AppendLine("MGFR setup check");
            report.AppendLine($"  Unity version      : {Application.unityVersion}");
            report.AppendLine($"  Active build target: {EditorUserBuildSettings.activeBuildTarget}");
            report.AppendLine($"  Colour space       : {PlayerSettings.colorSpace}   (want Linear)");
            report.AppendLine($"  Graphics APIs      : {DescribeGraphicsApis()}   (want Direct3D11)");
            report.AppendLine($"  Scripting backend  : {PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone)}   (want IL2CPP for the packaged run)");
            report.AppendLine($"  Render pipeline    : {DescribePipeline()}");
            report.AppendLine($"  OpenXR loader      : {DescribeOpenXrLoader()}");
            report.AppendLine($"  Active OpenXR runtime: {ReadActiveOpenXrRuntime()}");
            report.AppendLine($"  Smoke test scene   : {(System.IO.File.Exists(ScenePath) ? ScenePath : "MISSING - run MGFR > Create Smoke Test Scene")}");
            report.AppendLine($"  Scene in Build     : {(IsSceneInBuild() ? "yes" : "no")}");
            report.AppendLine($"  Character scene    : {(System.IO.File.Exists(CharacterScenePath) ? CharacterScenePath : "MISSING - run MGFR > Create Character Scene")}");
            report.AppendLine($"  Character in Build : {(IsCharacterSceneInBuild() ? "yes" : "no")}");
            report.AppendLine($"  Character data     : {DescribeCharacterData()}");
            Debug.Log(report.ToString());
        }

        /// <summary>
        /// Whether the runtime character data is actually on disk. The scene is
        /// built so that missing data is a readable message rather than a broken
        /// scene, so this is the check that says which of the two you are looking at.
        /// </summary>
        static string DescribeCharacterData()
        {
            var root = System.IO.Path.Combine(Application.dataPath, "StreamingAssets/si");
            var json = System.IO.Path.Combine(root, "si_model.json");
            var bin = System.IO.Path.Combine(root, "si_model.bin");

            if (!System.IO.File.Exists(json) || !System.IO.File.Exists(bin))
                return $"MISSING from {root} - run MGFR > Copy Character Data";

            var textures = System.IO.Directory.Exists(System.IO.Path.Combine(root, "textures"))
                ? System.IO.Directory.GetFiles(System.IO.Path.Combine(root, "textures")).Length
                : 0;

            return $"{new System.IO.FileInfo(bin).Length:N0} B bin, {textures} textures in {root}";
        }

        static string DescribeGraphicsApis()
        {
            try
            {
                var apis = PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
                if (apis == null || apis.Length == 0)
                    return "(none listed)";
                return string.Join(", ", apis.Select(a => a.ToString()));
            }
            catch (Exception e)
            {
                return $"(unreadable: {e.GetType().Name}: {e.Message})";
            }
        }

        static string DescribePipeline()
        {
            var asset = GraphicsSettings.defaultRenderPipeline;
            if (asset == null)
                return "Built-in - no URP asset assigned. See unity-client/README.md, 'Assign the URP asset'";

            return $"{asset.name} ({asset.GetType().Name})";
        }

        static string DescribeOpenXrLoader()
        {
            try
            {
                var general = XRGeneralSettingsPerBuildTarget
                    .XRGeneralSettingsForBuildTarget(BuildTargetGroup.Standalone);

                if (general == null)
                    return "not configured - open Project Settings > XR Plug-in Management";

                var manager = general.Manager;
                if (manager == null)
                    return "no manager - open Project Settings > XR Plug-in Management once";

                var loaders = manager.activeLoaders;
                if (loaders == null || loaders.Count == 0)
                    return "no loader enabled - tick OpenXR under Project Settings > XR Plug-in Management";

                return string.Join(", ", loaders.Select(l => l == null ? "null" : l.GetType().Name));
            }
            catch (Exception e)
            {
                return $"(unreadable: {e.GetType().Name}: {e.Message})";
            }
        }

        /// <summary>
        /// Cross-checks the one thing Unity cannot tell us: which OpenXR runtime
        /// the operating system will hand the application. On this machine it must
        /// be SteamVR's, not PICO Connect's.
        /// </summary>
        static string ReadActiveOpenXrRuntime()
        {
            try
            {
                using (var key = Registry.LocalMachine.OpenSubKey(OpenXrRegistryPath))
                {
                    if (key?.GetValue("ActiveRuntime") is string machine)
                        return machine;
                }

                using (var key = Registry.CurrentUser.OpenSubKey(OpenXrRegistryPath))
                {
                    if (key?.GetValue("ActiveRuntime") is string user)
                        return user;
                }

                return "(no ActiveRuntime value found)";
            }
            catch (Exception e)
            {
                return $"(unreadable: {e.GetType().Name}: {e.Message})";
            }
        }

        static bool IsSceneInBuild() => IsSceneInBuild(ScenePath);

        static bool IsCharacterSceneInBuild() => IsSceneInBuild(CharacterScenePath);

        static bool IsSceneInBuild(string path)
        {
            var scenes = EditorBuildSettings.scenes;
            return scenes != null && scenes.Any(s => s != null && s.path == path);
        }

        // ---- Configure ------------------------------------------------------

        [MenuItem(MenuRoot + "Configure Project", priority = 20)]
        public static void ConfigureProject()
        {
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.StandaloneWindows64)
            {
                if (!EditorUserBuildSettings.SwitchActiveBuildTarget(
                        BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64))
                {
                    Debug.LogWarning("[MGFR] could not switch the active build target to Windows x64. " +
                                     "The settings below still apply to it.");
                }
            }

            PlayerSettings.companyName = "MGFR";
            PlayerSettings.productName = "MGFR Smoke Test";

            // Linear is what the project wants long term. Note that it also moves
            // the background off a naive green unless the chroma-key value is
            // treated as sRGB, which is why the smoke test sets its background
            // from the same constant ALVR is configured against.
            PlayerSettings.colorSpace = ColorSpace.Linear;

            // A headset run leaves the desktop window unfocused for minutes at a
            // time. Without this the application stops rendering when it is not
            // focused.
            PlayerSettings.runInBackground = true;
            PlayerSettings.defaultScreenWidth = 1280;
            PlayerSettings.defaultScreenHeight = 720;

            // D3D11 only. ALVR's capture path is the one that has to be happy, and
            // it is happiest here. Do not let Unity pick D3D12 on this machine.
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
            PlayerSettings.SetGraphicsAPIs(
                BuildTarget.StandaloneWindows64,
                new[] { GraphicsDeviceType.Direct3D11 });

            // The packaged run in stage ④ is the one that counts, so build the
            // same way from the start.
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.IL2CPP);

            // The OpenXR plugin's input subsystem needs the Input System package,
            // and that package only receives events if the new input backend is
            // active. "Both" leaves the legacy Input Manager working too, so this
            // cannot break something that already worked.
            string inputHandling = SetActiveInputHandlingBoth();

            string xr = EnableOpenXrLoader();

            string shader = EnsureAlwaysIncludedShader(CharacterShaderName);

            AssetDatabase.SaveAssets();

            Debug.Log(
                "[MGFR] project configured.\n" +
                "  colour space      : Linear\n" +
                "  graphics API      : Direct3D11 only\n" +
                "  scripting backend : IL2CPP\n" +
                $"  input handling    : {inputHandling}\n" +
                $"  OpenXR loader     : {xr}\n" +
                $"  character shader  : {shader}\n" +
                "Run MGFR > Check Setup next.");
        }

        /// <summary>
        /// Adds the character shader to Graphics Settings' Always Included Shaders.
        ///
        /// <c>SiCharacterLoader</c> calls <c>Shader.Find</c> at runtime, which
        /// resolves against the AssetDatabase in the editor and therefore always
        /// works there. In a player it only finds shaders the build included, and
        /// nothing in the project holds a reference to this one - the material is
        /// created at runtime. Without this the editor looks perfect and the
        /// packaged build renders the character magenta, which is exactly the kind
        /// of failure that only shows up after packaging.
        /// </summary>
        public static string EnsureAlwaysIncludedShader(string shaderName)
        {
            var shader = Shader.Find(shaderName);
            if (shader == null)
                return $"NOT FOUND: {shaderName} - is Assets/MGFR/Shaders in the project?";

            try
            {
                var assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/GraphicsSettings.asset");
                if (assets == null || assets.Length == 0)
                    return $"unreadable - add {shaderName} under Project Settings > Graphics > Always Included Shaders";

                var settings = new SerializedObject(assets[0]);
                var array = settings.FindProperty("m_AlwaysIncludedShaders");
                if (array == null || !array.isArray)
                    return $"unreadable - add {shaderName} under Project Settings > Graphics > Always Included Shaders";

                for (var i = 0; i < array.arraySize; i++)
                {
                    if (array.GetArrayElementAtIndex(i).objectReferenceValue == shader)
                        return "already in Always Included Shaders";
                }

                array.InsertArrayElementAtIndex(array.arraySize);
                array.GetArrayElementAtIndex(array.arraySize - 1).objectReferenceValue = shader;
                settings.ApplyModifiedProperties();

                return "added to Always Included Shaders";
            }
            catch (Exception e)
            {
                return $"{e.GetType().Name} - add {shaderName} under Project Settings > Graphics > Always Included Shaders";
            }
        }

        /// <summary>
        /// Sets Active Input Handling to "Both" (0 = old, 1 = new, 2 = both).
        ///
        /// There is no public API for this field, so it is written through the
        /// serialised ProjectSettings asset. Unity only applies it on the next
        /// editor start, so the caller has to say so rather than assume it took.
        /// </summary>
        static string SetActiveInputHandlingBoth()
        {
            const string Fallback =
                "set it by hand: Edit > Project Settings > Player > Active Input Handling > Both";

            try
            {
                var assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
                if (assets == null || assets.Length == 0)
                    return $"unreadable - {Fallback}";

                var settings = new SerializedObject(assets[0]);
                var property = settings.FindProperty("activeInputHandler");
                if (property == null)
                    return $"unreadable - {Fallback}";

                if (property.intValue == 2)
                    return "already Both";

                property.intValue = 2;
                settings.ApplyModifiedProperties();
                return "set to Both - RESTART the editor for it to take effect";
            }
            catch (Exception e)
            {
                return $"{e.GetType().Name} - {Fallback}";
            }
        }

        static string EnableOpenXrLoader()
        {
            try
            {
                var general = XRGeneralSettingsPerBuildTarget
                    .XRGeneralSettingsForBuildTarget(BuildTargetGroup.Standalone);

                if (general == null)
                {
                    return "NOT enabled - open Project Settings > XR Plug-in Management, tick OpenXR " +
                           "for the Windows tab, then run Configure Project again";
                }

                var manager = general.Manager;
                if (manager == null)
                {
                    return "NOT enabled - open Project Settings > XR Plug-in Management once, " +
                           "then run Configure Project again";
                }

                var loaders = manager.activeLoaders;
                if (loaders != null && loaders.Any(l => l != null && l.GetType().FullName == OpenXrLoaderTypeName))
                    return "already enabled";

                if (XRPackageMetadataStore.AssignLoader(manager, OpenXrLoaderTypeName, BuildTargetGroup.Standalone))
                {
                    EditorUtility.SetDirty(manager);
                    AssetDatabase.SaveAssets();
                    return "enabled";
                }

                return "NOT enabled - tick OpenXR under Project Settings > XR Plug-in Management";
            }
            catch (Exception e)
            {
                return $"NOT enabled ({e.GetType().Name}: {e.Message}) - " +
                       "tick OpenXR under Project Settings > XR Plug-in Management";
            }
        }

        // ---- Scene ----------------------------------------------------------

        /// <summary>
        /// Makes an empty scene and puts it in Build Settings.
        ///
        /// It is empty on purpose: SmokeTestRig builds the whole rig at runtime, so
        /// there is exactly one definition of the test and no hand-written scene
        /// YAML to drift. An existing scene file is never overwritten, and a scene
        /// that is already open is left open.
        /// </summary>
        [MenuItem(MenuRoot + "Create Smoke Test Scene", priority = 21)]
        public static void CreateSmokeTestScene()
        {
            CreateScene(ScenePath, "MGFR.SmokeTest.SmokeTestRig builds the background, cube, " +
                                   "hand trackers and test tone at runtime.", 0);
        }

        /// <summary>
        /// The character scene. Empty for the same reason the smoke test is:
        /// <c>MGFR.Character.SiCharacterBootstrap</c> builds the camera, the light,
        /// the character and the dialogue stack at runtime, so there is no scene
        /// YAML to drift and no GUID references into the gitignored model data.
        ///
        /// It goes in front of the smoke test in Build Settings because it is the
        /// one that gets shipped; the smoke test is a regression baseline, not the
        /// product.
        /// </summary>
        [MenuItem(MenuRoot + "Create Character Scene", priority = 22)]
        public static void CreateCharacterScene()
        {
            CreateScene(CharacterScenePath,
                        "MGFR.Character.SiCharacterBootstrap builds the camera, light, " +
                        "character and dialogue stack at runtime. It needs the converted " +
                        "model: run MGFR > Copy Character Data first.", 0);
        }

        static void CreateScene(string scenePath, string explanation, int buildIndex)
        {
            if (!AssetDatabase.IsValidFolder(SceneFolder))
                AssetDatabase.CreateFolder("Assets/MGFR", "Scenes");

            string how;

            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) != null)
            {
                // Never overwrite: the file on disk may have been edited since it
                // was written, and Unity's SaveScene would replace it silently.
                how = "already existed, left alone";
            }
            else
            {
                how = WriteTheScene(scenePath);
                if (how == null)
                    return;
            }

            AddSceneToBuild(scenePath, buildIndex);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            Debug.Log($"[MGFR] {scenePath}: {how}, and it is in Build Settings. " +
                      "The scene is deliberately empty - " + explanation +
                      " Delete the file and run this again to have it regenerated.");

            EditorGUIUtility.PingObject(AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath));
        }

        /// <summary>
        /// Writes the empty scene, returning a description of how, or null if it
        /// could not be written.
        ///
        /// Unity refuses to create a scene additively while an untitled scene is
        /// open: "Cannot create a new scene additively with an untitled scene
        /// unsaved". An untitled scene has nowhere to be saved to, so it cannot be
        /// kept alongside a new one, and a project that has never had a scene saved
        /// is always in exactly that state. There the untitled scene has to be
        /// replaced instead, which is what NewSceneMode.Single does.
        /// </summary>
        static string WriteTheScene(string scenePath)
        {
            // Fully qualified: EditorSceneManager inherits the SceneManager statics,
            // but going through the base type needs no assumption about that.
            var active = UnityEngine.SceneManagement.SceneManager.GetActiveScene();

            if (!string.IsNullOrEmpty(active.path))
            {
                // A real scene is open, so add alongside it and leave it alone.
                var added = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);

                if (!EditorSceneManager.SaveScene(added, scenePath))
                {
                    Debug.LogError($"[MGFR] could not save the scene to {scenePath}.");
                    EditorSceneManager.CloseScene(added, true);
                    return null;
                }

                EditorSceneManager.CloseScene(added, true);
                return "created";
            }

            // Replacing the untitled scene discards it, so let the user save it
            // first if it has been changed. This returns true with no prompt when
            // there is nothing to save, which is the normal first-run case.
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                return null;

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            if (!EditorSceneManager.SaveScene(scene, scenePath))
            {
                Debug.LogError($"[MGFR] could not save the scene to {scenePath}.");
                return null;
            }

            return "created, replacing the untitled scene the editor opened with";
        }

        static void AddSceneToBuild(string scenePath, int index)
        {
            var scenes = EditorBuildSettings.scenes?.ToList() ?? new List<EditorBuildSettingsScene>();
            if (scenes.Any(s => s != null && s.path == scenePath))
                return;

            scenes.Insert(Mathf.Clamp(index, 0, scenes.Count), new EditorBuildSettingsScene(scenePath, true));
            EditorBuildSettings.scenes = scenes.ToArray();
        }

        // ---- Character data -------------------------------------------------

        /// <summary>
        /// Copies the offline conversion output into StreamingAssets, where
        /// <c>SiCharacterLoader</c> reads it at runtime.
        ///
        /// StreamingAssets rather than an imported asset because the data has to
        /// stay out of the repository, and because building the mesh at runtime
        /// means the scene holds no GUID reference that would break when the data
        /// is regenerated with fresh GUIDs.
        ///
        /// Both sides are regenerable, so this overwrites without asking - but it
        /// says what it replaced, because "the character looks wrong" and "the copy
        /// silently kept an old texture" are hard to tell apart otherwise.
        /// </summary>
        [MenuItem(MenuRoot + "Copy Character Data", priority = 23)]
        public static void CopyCharacterData()
        {
            var source = ConvertedPath;
            var destination = System.IO.Path.Combine(Application.dataPath, "StreamingAssets/si");

            if (!System.IO.Directory.Exists(source))
            {
                Debug.LogError(
                    $"[MGFR] converted data not found at {source}.\n" +
                    "Run the converter first:\n" +
                    "  python -I tools/pmx/convert_si.py \"<path to 祀.pmx>\" " + source + "\n" +
                    $"or set a different source with EditorPrefs '{ConvertedPathPrefKey}'.");
                return;
            }

            var required = new[] { "si_model.json", "si_model.bin" };
            foreach (var file in required)
            {
                if (!System.IO.File.Exists(System.IO.Path.Combine(source, file)))
                {
                    Debug.LogError($"[MGFR] {source} has no {file} - the conversion did not complete.");
                    return;
                }
            }

            var copied = 0;
            var overwritten = 0;

            try
            {
                System.IO.Directory.CreateDirectory(destination);

                foreach (var file in System.IO.Directory.GetFiles(source, "*", System.IO.SearchOption.AllDirectories))
                {
                    var relative = file.Substring(source.Length).TrimStart('\\', '/');
                    var target = System.IO.Path.Combine(destination, relative);
                    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));

                    if (System.IO.File.Exists(target))
                        overwritten++;

                    System.IO.File.Copy(file, target, true);
                    copied++;
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[MGFR] copy to {destination} failed after {copied} files: " +
                               $"{e.GetType().Name}: {e.Message}");
                return;
            }

            AssetDatabase.Refresh();

            Debug.Log($"[MGFR] character data: {copied} files copied from {source} to {destination} " +
                      $"({overwritten} replaced).\n" +
                      "This folder is gitignored - it is derived from the model and must not be committed.\n" +
                      "Regenerate the conversion with:\n" +
                      "  python -I tools/pmx/convert_si.py \"<path to 祀.pmx>\" " + source);
        }
    }
}
