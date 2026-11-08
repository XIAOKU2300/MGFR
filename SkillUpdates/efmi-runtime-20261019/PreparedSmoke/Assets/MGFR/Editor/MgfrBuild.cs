using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MGFR.EditorTools
{
    /// <summary>
    /// The packaging entry point.
    ///
    /// Two things make this more than a call to <c>BuildPipeline.BuildPlayer</c>.
    ///
    /// First, the character shader. <c>MGFR/Character</c> is referenced only by
    /// name at runtime, so nothing in the project holds a hard reference to it and
    /// the build would drop it. A dropped shader is not a build error - the build
    /// succeeds and the character renders magenta. This script puts it in Always
    /// Included Shaders before building, which is the same thing
    /// <c>MGFR &gt; Configure Project</c> does, and it is the reason
    /// <c>EnsureAlwaysIncludedShader</c> was made public.
    ///
    /// Second, the scripting backend. The project is set to IL2CPP, and IL2CPP
    /// needs a C++ toolchain that this machine does not have. Rather than fail
    /// with a Unity-internal error, this script checks for the toolchain and, when
    /// it is absent, says exactly which components are missing. It never installs
    /// anything and never reboots.
    ///
    /// The scene list is checked too: the character scene has to be enabled in
    /// Build Settings or the player would open the smoke test instead.
    /// </summary>
    public static class MgfrBuild
    {
        const string CharacterScenePath = "Assets/MGFR/Scenes/SiCharacter.unity";
        const string CharacterShaderName = "MGFR/Character";
        const string OutputFolder = "Build/Windows";
        const string OutputName = "MGFR.exe";
        const string ReportName = "build-report.txt";

        // ---- Menu items ------------------------------------------------------

        [MenuItem("MGFR/Build/Windows Development Player", priority = 60)]
        public static void MenuBuildDevelopment() => Run(true, false, false);

        [MenuItem("MGFR/Build/Windows Development Player (Mono)", priority = 61)]
        public static void MenuBuildDevelopmentMono() => Run(true, true, false);

        [MenuItem("MGFR/Build/Windows Release Player", priority = 62)]
        public static void MenuBuildRelease() => Run(false, false, false);

        // ---- Batch entry points ---------------------------------------------
        //
        // Unity -batchmode -quit -projectPath <dir> -executeMethod MGFR.EditorTools.MgfrBuild.PlayerMono
        //
        // These exit with a meaningful code, because a batch build that fails still
        // lets Unity exit 0 on its own.

        public static void Player() => Run(true, false, true);
        public static void PlayerMono() => Run(true, true, true);
        public static void PlayerRelease() => Run(false, false, true);

        // ---- The build -------------------------------------------------------

        static void Run(bool development, bool forceMono, bool batch)
        {
            var exitCode = 0;
            var report = new System.Text.StringBuilder();

            void Line(string text)
            {
                report.AppendLine(text);
                Debug.Log("[MGFR build] " + text);
            }

            var originalBackend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone);
            var originalProduct = PlayerSettings.productName;
            var backendChanged = false;
            var productChanged = false;

            try
            {
                Line($"unity            : {Application.unityVersion}");
                Line($"project          : {Directory.GetCurrentDirectory()}");
                Line($"pipeline         : {(UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline == null ? "built-in" : UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline.GetType().Name)}");
                Line($"colour space     : {QualitySettings.activeColorSpace}");
                Line($"target           : StandaloneWindows64, {(development ? "development" : "release")}");

                if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64))
                {
                    Line("ERROR: the Windows standalone build module is not installed in this editor.");
                    Line("       Install it from Unity Hub > Installs > this editor > Add modules.");
                    exitCode = 2;
                    return;
                }

                // ---- scripting backend ----

                var backend = originalBackend;
                if (forceMono && backend != ScriptingImplementation.Mono2x)
                {
                    PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
                    backendChanged = true;
                    backend = ScriptingImplementation.Mono2x;
                    Line($"scripting backend: {originalBackend} -> Mono for this build (the project setting is restored afterwards)");
                }
                else
                {
                    Line($"scripting backend: {backend}");
                }

                if (backend == ScriptingImplementation.IL2CPP)
                {
                    var missing = CppToolchain.MissingComponents();
                    if (missing.Length > 0)
                    {
                        Line("ERROR: the project is set to IL2CPP but the C++ toolchain is not complete.");
                        Line("       Missing:");
                        foreach (var m in missing)
                            Line("         - " + m);
                        Line("       IL2CPP cannot be built here. Either build the Mono player");
                        Line("       (MGFR > Build > Windows Development Player (Mono)), or install");
                        Line("       Visual Studio 2022 with the 'Desktop development with C++'");
                        Line("       workload plus the Windows 10/11 SDK. Nothing was installed and");
                        Line("       the machine was not restarted.");
                        exitCode = 3;
                        return;
                    }
                }

                // ---- the character shader ----

                var shader = MgfrEditorMenu.EnsureAlwaysIncludedShader(CharacterShaderName);
                Line($"always included  : {CharacterShaderName} - {shader}");

                if (string.IsNullOrEmpty(shader) || shader.StartsWith("NOT FOUND", StringComparison.Ordinal))
                {
                    Line("ERROR: the character shader is not in the project, so the build would render");
                    Line("       the character magenta. Check that Assets/MGFR/Shaders is present.");
                    exitCode = 4;
                    return;
                }

                if (!shader.StartsWith("added", StringComparison.Ordinal) &&
                    !shader.StartsWith("already", StringComparison.Ordinal))
                {
                    Line("WARNING: the shader could not be written into Always Included Shaders automatically.");
                    Line("         Add MGFR/Character by hand under Project Settings > Graphics >");
                    Line("         Always Included Shaders, or the packaged build renders magenta.");
                }

                // ---- the scene list ----

                var scenes = EditorBuildSettings.scenes
                    .Where(s => s != null && s.enabled)
                    .Select(s => s.path)
                    .ToArray();

                Line($"scenes           : {scenes.Length} enabled");
                foreach (var s in scenes)
                    Line($"  {s}");

                if (!scenes.Contains(CharacterScenePath))
                {
                    Line($"ERROR: {CharacterScenePath} is not enabled in Build Settings.");
                    Line("       Run MGFR > Create Character Scene, then enable it in File > Build Settings.");
                    Line("       Without it the player would open the smoke test instead of the character.");
                    exitCode = 5;
                    return;
                }

                if (scenes[0] != CharacterScenePath)
                    Line($"WARNING: {scenes[0]} is scene 0, so the player opens there. The character scene is still reachable.");

                // ---- the product name ----

                if (originalProduct != "MGFR")
                {
                    PlayerSettings.productName = "MGFR";
                    productChanged = true;
                    Line($"product name     : {originalProduct} -> MGFR for this build (restored afterwards)");
                }

                // ---- build ----

                Directory.CreateDirectory(OutputFolder);
                var outputPath = Path.Combine(OutputFolder, OutputName);
                var options = new BuildPlayerOptions
                {
                    scenes = scenes,
                    locationPathName = outputPath,
                    target = BuildTarget.StandaloneWindows64,
                    targetGroup = BuildTargetGroup.Standalone,
                    options = development
                        ? BuildOptions.Development | BuildOptions.AllowDebugging
                        : BuildOptions.None,
                };

                Line($"output           : {Path.GetFullPath(outputPath)}");
                Line("");
                Line("building...");

                var summary = BuildPipeline.BuildPlayer(options).summary;
                Line("");
                Line($"result           : {summary.result}");
                Line($"size             : {summary.totalSize / (1024 * 1024)} MB");
                Line($"time             : {summary.totalTime}");
                Line($"errors/warnings  : {summary.totalErrors} / {summary.totalWarnings}");
                Line($"output           : {summary.outputPath}");

                if (summary.result != BuildResult.Succeeded)
                {
                    Line("The build did not succeed. The Unity log above has the compiler or packaging error.");
                    exitCode = 6;
                }
                else
                {
                    Line("");
                    Line("Launch it with the services already running, for example:");
                    Line($"  {OutputName} -mgfr-selftest -mgfr-seconds 60 -mgfr-rounds 3 -mgfr-report {Path.GetFullPath(OutputFolder)}/selftest.txt");
                    Line($"  {OutputName}                      (normal desktop preview)");
                }
            }
            catch (Exception e)
            {
                Line("EXCEPTION: " + e);
                exitCode = 7;
            }
            finally
            {
                if (backendChanged)
                    PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, originalBackend);
                if (productChanged)
                    PlayerSettings.productName = originalProduct;
                if (backendChanged || productChanged)
                    AssetDatabase.SaveAssets();

                try
                {
                    Directory.CreateDirectory(OutputFolder);
                    File.WriteAllText(Path.Combine(OutputFolder, ReportName), report.ToString());
                }
                catch (Exception e)
                {
                    Debug.LogWarning("[MGFR build] could not write the build report: " + e.Message);
                }
            }

            if (batch)
                EditorApplication.Exit(exitCode);
        }

        /// <summary>
        /// Whether the C++ toolchain IL2CPP needs is present.
        ///
        /// Unity does not expose this through the API, so it is a filesystem check
        /// for the things Unity itself looks for. It is a heuristic: a machine can
        /// pass it and still fail to link. It is here to turn an unexplained IL2CPP
        /// failure into a named missing component, which is what the work order asks
        /// for - record what is missing, do not install it.
        /// </summary>
        static class CppToolchain
        {
            public static string[] MissingComponents()
            {
                var missing = new System.Collections.Generic.List<string>();

                var vswhere = @"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe";
                var hasVs = File.Exists(vswhere)
                            || Directory.Exists(@"C:\Program Files\Microsoft Visual Studio")
                            || Directory.Exists(@"C:\Program Files (x86)\Microsoft Visual Studio");

                if (!hasVs)
                    missing.Add("Visual Studio (no Installer\\vswhere.exe and no Microsoft Visual Studio directory)");

                if (!Directory.Exists(@"C:\Program Files (x86)\Windows Kits\10\Include"))
                    missing.Add("Windows 10/11 SDK (no C:\\Program Files (x86)\\Windows Kits\\10\\Include)");

                if (FindOnPath("cl.exe") == null && !HasMsvcToolset())
                    missing.Add("MSVC C++ compiler (no cl.exe on PATH and no MSVC toolset directory)");

                return missing.ToArray();
            }

            static bool HasMsvcToolset()
            {
                foreach (var root in new[] { @"C:\Program Files\Microsoft Visual Studio", @"C:\Program Files (x86)\Microsoft Visual Studio" })
                {
                    if (!Directory.Exists(root))
                        continue;

                    try
                    {
                        if (Directory.EnumerateDirectories(root, "MSVC", SearchOption.AllDirectories).Any())
                            return true;
                    }
                    catch (UnauthorizedAccessException) { }
                    catch (IOException) { }
                }

                return false;
            }

            static string FindOnPath(string exe)
            {
                var path = Environment.GetEnvironmentVariable("PATH");
                if (string.IsNullOrEmpty(path))
                    return null;

                foreach (var dir in path.Split(Path.PathSeparator))
                {
                    if (string.IsNullOrWhiteSpace(dir))
                        continue;

                    try
                    {
                        var candidate = Path.Combine(dir.Trim(), exe);
                        if (File.Exists(candidate))
                            return candidate;
                    }
                    catch (ArgumentException) { }
                }

                return null;
            }
        }
    }
}
