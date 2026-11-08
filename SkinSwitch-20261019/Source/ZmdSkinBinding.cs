using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Character;

namespace MGFR.RenderStyles.ZmdEndfield
{
    public sealed partial class ZmdRenderStyle
    {
        sealed class SkinVariant
        {
            public Mesh rawMesh, outlinedMesh;
            public Material[] current, zmd;
            public bool ownsCurrent;
        }
        readonly Dictionary<SiAppearance, SkinVariant> skinVariants = new Dictionary<SiAppearance, SkinVariant>();
        Texture2D neutralSkinPacked;
        public SiAppearance OriginalAppearance { get; private set; }
        public bool SkinSwitchingEnabled { get; set; }

        void CacheOriginalAppearance()
        {
            OriginalAppearance = Loader.CaptureAppearance("original", previousMesh, PreviousMaterials);
            skinVariants.Add(OriginalAppearance, new SkinVariant {
                rawMesh = previousMesh, outlinedMesh = zmdMesh, current = PreviousMaterials, zmd = ZmdMaterials
            });
        }

        public void BindAppearance(SiAppearance appearance)
        {
            if (!IsReady) throw new InvalidOperationException("Render style is not ready.");
            if (!skinVariants.TryGetValue(appearance, out var variant))
            {
                var template = skinVariants[OriginalAppearance];
                variant = new SkinVariant {
                    rawMesh = appearance.Mesh, current = new Material[appearance.Materials.Length],
                    zmd = new Material[appearance.Materials.Length], ownsCurrent = true
                };
                variant.rawMesh.RecalculateTangents();
                variant.outlinedMesh = Instantiate(variant.rawMesh);
                variant.outlinedMesh.name = appearance.Id + " ZMD smooth outline";
                PrepareOutlineNormals(variant.outlinedMesh);
                if (neutralSkinPacked == null)
                {
                    neutralSkinPacked = new Texture2D(1, 1, TextureFormat.RGBA32, false, true);
                    neutralSkinPacked.name = "Neutral swimsuit dielectric; source L channels unverified";
                    neutralSkinPacked.SetPixel(0, 0, new Color(0, .5f, 1, .45f));
                    neutralSkinPacked.Apply(false, true);
                }
                for (int i = 0; i < variant.current.Length; i++)
                {
                    var source = appearance.Materials[i];
                    variant.current[i] = new Material(template.current[i]) { name = source.name + " current skin" };
                    variant.zmd[i] = new Material(template.zmd[i]) { name = source.name + " ZMD skin" };
                    foreach (var material in new[] { variant.current[i], variant.zmd[i] })
                    {
                        Set(material, "_MainTex", source.GetTexture("_MainTex"));
                        Set(material, "_BaseColor", source.GetTexture("_MainTex"));
                        Set(material, "_Color", source.GetColor("_Color"));
                        foreach (string property in new[] { "_Cull", "_SrcBlend", "_DstBlend", "_ZWrite" })
                            Set(material, property, source.GetFloat(property));
                        material.renderQueue = source.renderQueue;
                    }
                }
                string manifest = Path.Combine(appearance.DataRoot, "skin.json");
                if (File.Exists(manifest))
                {
                    var profile = JsonUtility.FromJson<RenderSkinManifest>(File.ReadAllText(manifest));
                    if (profile.materialBindings != null) foreach (var binding in profile.materialBindings)
                    {
                        if (binding.slots == null || string.IsNullOrEmpty(binding.normalData)) continue;
                        string normalPath = SafeSkinPath(appearance.DataRoot, binding.normalData);
                        var normal = Load("skin/" + normalPath, () => File.ReadAllBytes(normalPath), true);
                        normal.wrapMode = TextureWrapMode.Repeat;
                        foreach (int slot in binding.slots)
                        {
                            if (slot < 0 || slot >= variant.current.Length) throw new InvalidDataException("Invalid skin material slot.");
                            var old = variant.current[slot]; var zmd = variant.zmd[slot];
                            Set(old, "_NormalData", normal); Set(zmd, "_NormalMap", normal);
                            Set(old, "_NormalStrength", slot == 7 ? .18f : .35f);
                            Set(zmd, "_ZmdNormalScale", slot == 7 ? .55f : 1f);
                            if (slot == 7) continue;
                            // L is source light data, not the original costume's P map.
                            // Use explicit dielectric roughness until its channels are documented.
                            Set(old, "_PackedData", neutralSkinPacked); Set(zmd, "_MOR", neutralSkinPacked);
                            Set(old, "_EmissionMap", Texture2D.blackTexture); Set(zmd, "_Emission", Texture2D.blackTexture);
                            Set(old, "_EmissionStrength", 0); Set(zmd, "_EmissionIntensity", 0);
                            Set(zmd, "_Roughness", .02f); Set(zmd, "_Metallic", 0);
                            Set(zmd, "_SpecularIntensity", slot == 10 ? .4f : .9f);
                            Set(zmd, "_EnvSpecularIntensity", .2f);
                            Set(zmd, "_NormalStrength", .38f);
                        }
                    }
                }
                skinVariants.Add(appearance, variant);
            }
            previousMesh = variant.rawMesh; zmdMesh = variant.outlinedMesh;
            PreviousMaterials = variant.current; ZmdMaterials = variant.zmd;
            SetActive(Active);
        }

        static string SafeSkinPath(string root, string relative)
        {
            string prefix = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string resolved = Path.GetFullPath(Path.Combine(prefix, relative));
            if (!resolved.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Skin texture path escapes the skin folder.");
            return resolved;
        }
        void DisposeSkinVariants()
        {
            foreach (var variant in skinVariants.Values)
            {
                for (int i = 0; i < variant.zmd.Length; i++)
                {
                    if (variant.zmd[i] != variant.current[i] || variant.ownsCurrent) Destroy(variant.zmd[i]);
                    if (variant.ownsCurrent) Destroy(variant.current[i]);
                }
                if (variant.outlinedMesh != null) Destroy(variant.outlinedMesh);
            }
            if (neutralSkinPacked != null) Destroy(neutralSkinPacked);
        }
        [Serializable] sealed class RenderSkinManifest { public RenderSkinBinding[] materialBindings; }
        [Serializable] sealed class RenderSkinBinding { public int[] slots; public string normalData; }
    }
}
