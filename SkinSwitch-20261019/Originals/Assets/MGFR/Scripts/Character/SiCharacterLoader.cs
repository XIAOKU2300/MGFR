using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

namespace MGFR.Character
{
    /// <summary>
    /// Builds the converted 祀 model at runtime from the files
    /// <c>tools/pmx/convert_si.py</c> writes.
    ///
    /// Why runtime rather than an imported asset
    /// -----------------------------------------
    /// The obvious alternative is an editor importer that saves Mesh, Material and
    /// Texture assets and lets the scene reference them. That fails here for a
    /// reason specific to this project: every byte of the character is derived from
    /// 祀, whose ReadMe forbids redistribution, so all of it has to stay out of the
    /// repository. A scene holding GUID references into a gitignored folder is a
    /// scene that breaks for anyone who clones it, and regenerating the assets
    /// mints fresh GUIDs and breaks the references again.
    ///
    /// Building at runtime sidesteps that completely. The scene holds only a
    /// component; the data is a file path. A clone without the data still loads the
    /// scene and reports "character data missing" in the HUD, which is a far better
    /// failure than a scene full of missing references.
    ///
    /// The cost is load time, which is measured and logged rather than assumed.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SiCharacterLoader : MonoBehaviour
    {
        public const string JsonFileName = "si_model.json";
        public const string BinFileName = "si_model.bin";
        public const string TextureFolderName = "textures";

        [Tooltip("Folder under StreamingAssets holding si_model.json, si_model.bin and textures/.")]
        public string dataFolder = "si";

        [Tooltip("Absolute path to read instead of StreamingAssets/si. Empty means use StreamingAssets.")]
        public string dataRootOverride = string.Empty;

        [Tooltip("Build the character during Start(). Turn off to drive Build() by hand.")]
        public bool buildOnStart = true;

        [Tooltip("Log every material's resolved blend/cull state. Useful when the model looks wrong.")]
        public bool logMaterialTable = true;

        // ---- Results --------------------------------------------------------

        public bool IsReady { get; private set; }
        public string Status { get; private set; } = "not built yet";
        public SiModelData Data { get; private set; }
        public SkinnedMeshRenderer Renderer { get; private set; }
        public Transform BonesRoot { get; private set; }
        public Material[] Materials { get; private set; } = Array.Empty<Material>();
        public string[] BlendShapeNames { get; private set; } = Array.Empty<string>();
        public float BuildSeconds { get; private set; }

        /// <summary>Local-space bounds of the built mesh, metres.</summary>
        public Bounds LocalBounds { get; private set; }

        readonly Dictionary<string, int> _blendShapeLookup = new Dictionary<string, int>(StringComparer.Ordinal);

        Color[] _materialBaseDiffuse;
        Color[] _materialBaseSpecular;
        Color[] _materialBaseAmbient;
        float[] _materialBaseSpecularStrength;

        int _blushMorphIndex = -1;
        int _blushMaterialIndex = -1;

        void Start()
        {
            if (buildOnStart)
                Build();
        }

        public static string ResolveDataRoot(string folder, string overridePath)
        {
            if (!string.IsNullOrWhiteSpace(overridePath))
                return overridePath;
            return Path.Combine(Application.streamingAssetsPath, folder);
        }

        public void Build()
        {
            if (IsReady)
                return;

            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            var root = ResolveDataRoot(dataFolder, dataRootOverride);
            var jsonPath = Path.Combine(root, JsonFileName);
            var binPath = Path.Combine(root, BinFileName);

            if (!File.Exists(jsonPath) || !File.Exists(binPath))
            {
                // The single most likely first-run failure, so it says exactly what
                // to do rather than throwing into the console.
                Status = $"character data missing at {root} - run MGFR > Copy Character Data";
                Debug.LogWarning($"[SiCharacterLoader] {Status}");
                return;
            }

            try
            {
                Data = JsonUtility.FromJson<SiModelData>(File.ReadAllText(jsonPath));
                if (Data == null || Data.counts == null || Data.counts.vertices <= 0)
                {
                    Status = $"{JsonFileName} parsed but has no counts - converter output and SiModelData are out of step";
                    Debug.LogError($"[SiCharacterLoader] {Status}");
                    return;
                }

                var mesh = BuildMesh(File.ReadAllBytes(binPath), Data);
                BuildBones(Data);
                BuildMaterials(Data, root);
                AttachRenderer(mesh);
                CacheMaterialMorphBase(Data);

                IsReady = true;
                BuildSeconds = stopwatch.ElapsedMilliseconds / 1000f;
                Status = $"built in {BuildSeconds:F2} s: {Data.counts.vertices:N0} verts, "
                       + $"{Data.counts.indices / 3:N0} tris, {Data.counts.materials} materials, "
                       + $"{Data.counts.blendShapes} blend shapes, {Data.counts.bones} bones";

                Debug.Log($"[SiCharacterLoader] {Status}");
                if (logMaterialTable)
                    LogMaterialTable();
            }
            catch (Exception error)
            {
                Status = $"build failed: {error.GetType().Name}: {error.Message}";
                Debug.LogError($"[SiCharacterLoader] {Status}\n{error}");
            }
        }

        // ---- Mesh -----------------------------------------------------------

        static Mesh BuildMesh(byte[] binary, SiModelData data)
        {
            var counts = data.counts;
            var mesh = new Mesh { name = "Si" };

            // 219,111 indices is well past the 65,535 that a UInt16 index buffer
            // can address, so this is not optional.
            mesh.indexFormat = IndexFormat.UInt32;

            using (var stream = new MemoryStream(binary, writable: false))
            using (var reader = new BinaryReader(stream))
            {
                var magic = reader.ReadUInt32();
                var version = reader.ReadUInt32();
                if (magic != 0x5346474D)
                    throw new InvalidDataException($"bad binary magic 0x{magic:X8}, expected 0x5346474D");
                if (version != 1)
                    throw new InvalidDataException($"unsupported binary version {version}");

                var vertexCount = counts.vertices;

                var rawPositions = ReadFloats(reader, vertexCount * 3);
                var rawNormals = ReadFloats(reader, vertexCount * 3);
                var rawUvs = ReadFloats(reader, vertexCount * 2);
                var rawBoneIndices = ReadUInt16s(reader, vertexCount * 4);
                var rawBoneWeights = ReadFloats(reader, vertexCount * 4);
                var rawIndices = ReadUInt32s(reader, counts.indices);
                var rawBindposes = ReadFloats(reader, counts.bones * 16);
                var rawSubmesh = ReadUInt32s(reader, counts.materials * 2);

                var vertices = new Vector3[vertexCount];
                for (var i = 0; i < vertexCount; i++)
                    vertices[i] = new Vector3(rawPositions[i * 3], rawPositions[i * 3 + 1], rawPositions[i * 3 + 2]);

                var normals = new Vector3[vertexCount];
                for (var i = 0; i < vertexCount; i++)
                    normals[i] = new Vector3(rawNormals[i * 3], rawNormals[i * 3 + 1], rawNormals[i * 3 + 2]);

                var uvs = new Vector2[vertexCount];
                for (var i = 0; i < vertexCount; i++)
                    uvs[i] = new Vector2(rawUvs[i * 2], rawUvs[i * 2 + 1]);

                var weights = new BoneWeight[vertexCount];
                for (var i = 0; i < vertexCount; i++)
                {
                    weights[i] = new BoneWeight
                    {
                        boneIndex0 = rawBoneIndices[i * 4],
                        boneIndex1 = rawBoneIndices[i * 4 + 1],
                        boneIndex2 = rawBoneIndices[i * 4 + 2],
                        boneIndex3 = rawBoneIndices[i * 4 + 3],
                        weight0 = rawBoneWeights[i * 4],
                        weight1 = rawBoneWeights[i * 4 + 1],
                        weight2 = rawBoneWeights[i * 4 + 2],
                        weight3 = rawBoneWeights[i * 4 + 3],
                    };
                }

                var bindposes = new Matrix4x4[counts.bones];
                for (var b = 0; b < counts.bones; b++)
                {
                    var o = b * 16;

                    // The converter writes these row by row, and the check that
                    // settled it is that the rest pose has identity rotations: the
                    // inverse bind matrix is then the negated bone position, and
                    // that value turns up at raw[3], raw[7], raw[11] - the fourth
                    // element of each row - for every bone.
                    //
                    // SetRow, not the four-argument constructor. That constructor
                    // takes COLUMNS despite reading like it takes rows, so feeding
                    // it a row-major stream transposes every matrix. A transposed
                    // inverse bind matrix still produces a mesh with plausible
                    // bounds, which is why this was invisible: the skinned result
                    // lands tens of metres away from the model and the frame comes
                    // out empty, with nothing in the console.
                    var matrix = new Matrix4x4();
                    matrix.SetRow(0, new Vector4(rawBindposes[o + 0], rawBindposes[o + 1], rawBindposes[o + 2], rawBindposes[o + 3]));
                    matrix.SetRow(1, new Vector4(rawBindposes[o + 4], rawBindposes[o + 5], rawBindposes[o + 6], rawBindposes[o + 7]));
                    matrix.SetRow(2, new Vector4(rawBindposes[o + 8], rawBindposes[o + 9], rawBindposes[o + 10], rawBindposes[o + 11]));
                    matrix.SetRow(3, new Vector4(rawBindposes[o + 12], rawBindposes[o + 13], rawBindposes[o + 14], rawBindposes[o + 15]));
                    bindposes[b] = matrix;
                }

                mesh.SetVertices(vertices);
                mesh.SetNormals(normals);
                mesh.SetUVs(0, uvs);
                mesh.boneWeights = weights;
                mesh.bindposes = bindposes;

                mesh.subMeshCount = counts.materials;
                var triangles = new int[rawIndices.Length];
                for (var i = 0; i < rawIndices.Length; i++)
                    triangles[i] = (int)rawIndices[i];

                for (var m = 0; m < counts.materials; m++)
                {
                    var start = (int)rawSubmesh[m * 2];
                    var count = (int)rawSubmesh[m * 2 + 1];
                    if (count == 0)
                    {
                        mesh.SetTriangles(Array.Empty<int>(), m, false);
                        continue;
                    }
                    var slice = new int[count];
                    Array.Copy(triangles, start, slice, 0, count);
                    mesh.SetTriangles(slice, m, false);
                }

                // Blend shapes go in after the base mesh exists. Unity wants full
                // length delta arrays - one entry per vertex, zero for untouched
                // vertices - so one scratch buffer is reused and cleared per shape
                // rather than allocating 40 x 762 KB.
                var deltaVertices = new Vector3[vertexCount];
                for (var s = 0; s < data.blendShapes.Length; s++)
                {
                    var shape = data.blendShapes[s];
                    Array.Clear(deltaVertices, 0, vertexCount);

                    var indices = ReadUInt32s(reader, shape.vertexCount);
                    var deltas = ReadFloats(reader, shape.vertexCount * 3);
                    for (var k = 0; k < shape.vertexCount; k++)
                    {
                        deltaVertices[indices[k]] = new Vector3(deltas[k * 3], deltas[k * 3 + 1], deltas[k * 3 + 2]);
                    }

                    // 100 is the weight at which MMD applies the shape at full
                    // strength; the runtime then drives 0..1 and scales, which keeps
                    // the numbers in the HUD readable.
                    mesh.AddBlendShapeFrame(shape.name, 100f, deltaVertices, null, null);
                }
            }

            mesh.RecalculateBounds();
            return mesh;
        }

        static float[] ReadFloats(BinaryReader reader, int count)
        {
            var bytes = reader.ReadBytes(count * 4);
            var values = new float[count];
            Buffer.BlockCopy(bytes, 0, values, 0, bytes.Length);
            return values;
        }

        static ushort[] ReadUInt16s(BinaryReader reader, int count)
        {
            var bytes = reader.ReadBytes(count * 2);
            var values = new ushort[count];
            Buffer.BlockCopy(bytes, 0, values, 0, bytes.Length);
            return values;
        }

        static uint[] ReadUInt32s(BinaryReader reader, int count)
        {
            var bytes = reader.ReadBytes(count * 4);
            var values = new uint[count];
            Buffer.BlockCopy(bytes, 0, values, 0, bytes.Length);
            return values;
        }

        // ---- Bones ----------------------------------------------------------

        /// <summary>
        /// Every bone transform, in bone-index order. The mesh's bone weights are
        /// indices into this array, so the order is not a presentation detail - it is
        /// the contract between the mesh and the renderer.
        /// </summary>
        Transform[] _boneTransforms;

        void BuildBones(SiModelData data)
        {
            var bonesRoot = new GameObject("Bones");
            bonesRoot.transform.SetParent(transform, false);
            BonesRoot = bonesRoot.transform;

            var count = data.bones.Length;

            // Kept on the instance rather than left local: the renderer needs this
            // exact array, and it cannot be recovered from the hierarchy afterwards
            // because reparenting destroys the index order.
            _boneTransforms = new Transform[count];
            var transforms = _boneTransforms;
            var usedNames = new HashSet<string>(StringComparer.Ordinal);

            // Two passes: create everything, then parent. PMX stores parents before
            // children in practice, but relying on that would turn a malformed file
            // into an index-out-of-range instead of a sensible error.
            for (var i = 0; i < count; i++)
            {
                var name = data.bones[i].name;
                if (string.IsNullOrEmpty(name))
                    name = $"bone_{i}";
                if (!usedNames.Add(name))
                    name = $"{name}_{i}";

                var go = new GameObject(name);
                transforms[i] = go.transform;
            }

            for (var i = 0; i < count; i++)
            {
                var bone = data.bones[i];
                var parent = bone.parent >= 0 && bone.parent < count ? transforms[bone.parent] : bonesRoot.transform;
                transforms[i].SetParent(parent, false);

                var local = bone.localScaled;
                if (local != null && local.Length >= 3)
                    transforms[i].localPosition = new Vector3(local[0], local[1], local[2]);
            }
        }

        // ---- Materials ------------------------------------------------------

        enum AlphaMode
        {
            /// <summary>No texture alpha and no material alpha: blend off, depth on.</summary>
            Opaque,
            /// <summary>Texture alpha, material alpha 1: blend on but keep writing depth.</summary>
            BlendKeepDepth,
            /// <summary>Material alpha below 1: blend on, depth off.</summary>
            BlendNoDepth,
        }

        void BuildMaterials(SiModelData data, string root)
        {
            var shader = Shader.Find("MGFR/Character");
            if (shader == null)
                throw new InvalidOperationException("shader 'MGFR/Character' not found - is Assets/MGFR/Shaders/MgfrCharacter.shader imported?");

            var textureFolder = Path.Combine(root, TextureFolderName);
            var textureCache = new Dictionary<string, Texture2D>(StringComparer.OrdinalIgnoreCase);
            var textureHasAlpha = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);

            var materials = new Material[data.materials.Length];
            var table = new List<string>();

            for (var i = 0; i < data.materials.Length; i++)
            {
                var source = data.materials[i];
                var material = new Material(shader) { name = $"{i:00}_{source.name}" };

                var diffuse = ToColor(source.diffuse, Color.white);
                material.SetColor("_Color", diffuse);
                material.SetColor("_SpecTint", ToColor(source.specular, Color.black) * Mathf.Clamp01(source.specularStrength));
                material.SetColor("_AmbientColor", ToColor(source.ambient, new Color(0.25f, 0.25f, 0.25f, 1f)));
                // PMX has no smoothness; MMD's specular is sharp, so a mid value
                // keeps highlights from spreading over the whole face.
                material.SetFloat("_Glossiness", 0.35f);

                var hasTexture = false;
                if (!string.IsNullOrEmpty(source.textureFile))
                {
                    if (!textureCache.TryGetValue(source.textureFile, out var texture))
                    {
                        var path = Path.Combine(textureFolder, source.textureFile);
                        if (File.Exists(path))
                        {
                            texture = LoadTexture(path);
                            textureHasAlpha[source.textureFile] = HasAlpha(texture);
                        }
                        else
                        {
                            Debug.LogWarning($"[SiCharacterLoader] material {source.name}: texture {path} not found");
                        }
                        textureCache[source.textureFile] = texture;
                    }

                    if (texture != null)
                    {
                        material.SetTexture("_MainTex", texture);
                        material.mainTexture = texture;
                        hasTexture = true;
                    }
                }

                var textureAlpha = hasTexture && textureHasAlpha.TryGetValue(source.textureFile, out var a) && a;

                AlphaMode mode;
                // Cloth1Alpha is the authored sheer skirt panel. Its diffuse alpha
                // is 1, while translucency comes from the shared texture atlas.
                // Draw it after opaque clothing without letting it occlude the
                // legs/inner garment through the depth buffer.
                if (source.name == "Cloth1Alpha" || diffuse.a < 0.999f)
                    mode = AlphaMode.BlendNoDepth;
                else if (textureAlpha)
                    mode = AlphaMode.BlendKeepDepth;
                else
                    mode = AlphaMode.Opaque;

                switch (mode)
                {
                    case AlphaMode.Opaque:
                        material.SetFloat("_SrcBlend", (float)BlendMode.One);
                        material.SetFloat("_DstBlend", (float)BlendMode.Zero);
                        material.SetFloat("_ZWrite", 1f);
                        material.renderQueue = (int)RenderQueue.Geometry;
                        break;
                    case AlphaMode.BlendKeepDepth:
                        material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                        material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                        material.SetFloat("_ZWrite", 1f);
                        // Ahead of the genuinely translucent overlays but still after
                        // everything opaque, so the skirt does not sort against itself.
                        material.renderQueue = (int)RenderQueue.AlphaTest + 50;
                        break;
                    default:
                        material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                        material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                        material.SetFloat("_ZWrite", 0f);
                        material.renderQueue = (int)RenderQueue.Transparent;
                        break;
                }

                material.SetFloat("_Cull", source.isTwoSided ? (float)CullMode.Off : (float)CullMode.Back);

                materials[i] = material;
                table.Add($"  {i,2} {source.name,-12} queue={material.renderQueue,4} zwrite={material.GetFloat("_ZWrite")} "
                        + $"cull={(source.isTwoSided ? "off" : "back"),-4} alpha={diffuse.a:F2} mode={mode}"
                        + (textureAlpha ? " (texture has alpha)" : string.Empty));
            }

            Materials = materials;

            var names = new string[data.blendShapes.Length];
            for (var i = 0; i < data.blendShapes.Length; i++)
            {
                names[i] = data.blendShapes[i].name;
                _blendShapeLookup[names[i]] = i;
            }
            BlendShapeNames = names;

            _materialTable = table;
        }

        List<string> _materialTable;

        void AttachRenderer(Mesh mesh)
        {
            var renderer = gameObject.AddComponent<SkinnedMeshRenderer>();
            renderer.sharedMesh = mesh;
            renderer.sharedMaterials = Materials;
            renderer.rootBone = BonesRoot;

            // Every bone, in bone-index order - not the bones root's children.
            //
            // This was wrong, and it was wrong in the one way that hides itself: the
            // three children of the bones root were handed over as the bone array
            // against 828 bind poses, and a SkinnedMeshRenderer whose bone count does
            // not match the mesh's bind pose count draws nothing at all. The scene
            // loaded, the console was clean, and the only symptom was an empty frame.
            renderer.bones = _boneTransforms;

            // The character is moved around by the placement controls, and a
            // skinned renderer that leaves its original bounds stops drawing as soon
            // as it is considered off-screen. For one character that cost is
            // irrelevant and the alternative is an invisible model.
            renderer.updateWhenOffscreen = true;

            Renderer = renderer;
            LocalBounds = mesh.bounds;
        }

        static Texture2D LoadTexture(string path)
        {
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, mipChain: true);
            texture.LoadImage(File.ReadAllBytes(path), markNonReadable: false);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.filterMode = FilterMode.Bilinear;
            texture.anisoLevel = 2;
            return texture;
        }

        /// <summary>
        /// Whether any pixel is not fully opaque.
        ///
        /// MMD decides per material whether to alpha blend, but the PMX material
        /// record only carries the diffuse alpha - the texture's own alpha is the
        /// other half of the decision, and it is not recorded anywhere in the file.
        /// So it is measured. Cloth1 is the case that matters: its material alpha is
        /// 1.0 but its texture runs down to 108/255.
        /// </summary>
        static bool HasAlpha(Texture2D texture)
        {
            try
            {
                var pixels = texture.GetPixels32();
                for (var i = 0; i < pixels.Length; i++)
                {
                    if (pixels[i].a < 255)
                        return true;
                }
                return false;
            }
            catch (Exception)
            {
                // Not readable, or a format GetPixels32 cannot handle. Assuming no
                // alpha is the safer default: it renders opaque rather than
                // invisible.
                return false;
            }
        }

        static Color ToColor(float[] rgba, Color fallback)
        {
            if (rgba == null || rgba.Length < 3)
                return fallback;
            return new Color(rgba[0], rgba[1], rgba[2], rgba.Length > 3 ? rgba[3] : 1f);
        }

        void LogMaterialTable()
        {
            if (_materialTable == null)
                return;
            Debug.Log("[SiCharacterLoader] material table\n" + string.Join("\n", _materialTable));
        }

        // ---- Blend shapes ---------------------------------------------------

        public int BlendShapeCount => BlendShapeNames.Length;

        public int FindBlendShape(string name)
        {
            if (string.IsNullOrEmpty(name))
                return -1;
            return _blendShapeLookup.TryGetValue(name, out var index) ? index : -1;
        }

        public void SetBlendShape(int index, float weight)
        {
            if (Renderer == null || Renderer.sharedMesh == null)
                return;
            if (index < 0 || index >= BlendShapeNames.Length)
                return;
            Renderer.SetBlendShapeWeight(index, Mathf.Clamp(weight, 0f, 100f));
        }

        public float GetBlendShape(int index)
        {
            if (Renderer == null || index < 0 || index >= BlendShapeNames.Length)
                return 0f;
            return Renderer.GetBlendShapeWeight(index);
        }

        public void SetBlendShape(string name, float weight)
        {
            SetBlendShape(FindBlendShape(name), weight);
        }

        public void ZeroBlendShapes()
        {
            for (var i = 0; i < BlendShapeNames.Length; i++)
                SetBlendShape(i, 0f);
        }

        // ---- Material morphs ------------------------------------------------

        void CacheMaterialMorphBase(SiModelData data)
        {
            if (data.materialMorphs == null || data.materialMorphs.Length == 0)
                return;

            _materialBaseDiffuse = new Color[Materials.Length];
            _materialBaseSpecular = new Color[Materials.Length];
            _materialBaseAmbient = new Color[Materials.Length];
            _materialBaseSpecularStrength = new float[Materials.Length];

            for (var i = 0; i < Materials.Length; i++)
            {
                _materialBaseDiffuse[i] = Materials[i].GetColor("_Color");
                _materialBaseSpecular[i] = Materials[i].GetColor("_SpecTint");
                _materialBaseAmbient[i] = Materials[i].GetColor("_AmbientColor");
                _materialBaseSpecularStrength[i] = data.materials[i].specularStrength;
            }

            // Only one morph in this model, but the lookup is by name so a future
            // model with several does not need a code change.
            var wanted = data.runtimeHints != null ? data.runtimeHints.blushMaterialMorph : null;
            for (var i = 0; i < data.materialMorphs.Length; i++)
            {
                if (!string.IsNullOrEmpty(wanted) && data.materialMorphs[i].name == wanted)
                {
                    _blushMorphIndex = i;
                    if (data.materialMorphs[i].offsets != null && data.materialMorphs[i].offsets.Length > 0)
                        _blushMaterialIndex = data.materialMorphs[i].offsets[0].material;
                    break;
                }
            }
        }

        /// <summary>Material morphs that exist, by name.</summary>
        public string[] MaterialMorphNames
        {
            get
            {
                if (Data?.materialMorphs == null)
                    return Array.Empty<string>();
                var names = new string[Data.materialMorphs.Length];
                for (var i = 0; i < names.Length; i++)
                    names[i] = Data.materialMorphs[i].name;
                return names;
            }
        }

        /// <summary>
        /// Apply a material morph at <paramref name="weight"/> in 0..1.
        ///
        /// This is deliberately not a blend shape. docs/constraints.md #5 requires
        /// material morphs to be classified individually, and the whole point of the
        /// classification is that animating a BlendShape named 照れ would look
        /// implemented while doing nothing at all - the mesh has no 照れ blend shape,
        /// because the PMX stores it as a change to material 11 (表情), not to
        /// vertices. For this model the change is a single channel: the overlay's
        /// diffuse alpha goes 0.00 to 1.00, so the blush fades in. Every other offset
        /// channel (specular, ambient, edge, texture/sphere/toon tint) is zero in the
        /// source data, which is why they are not wired up.
        /// </summary>
        public void SetMaterialMorphWeight(int morphIndex, float weight)
        {
            if (Data?.materialMorphs == null || _materialBaseDiffuse == null)
                return;
            if (morphIndex < 0 || morphIndex >= Data.materialMorphs.Length)
                return;

            weight = Mathf.Clamp01(weight);
            var morph = Data.materialMorphs[morphIndex];
            if (morph.offsets == null)
                return;

            foreach (var offset in morph.offsets)
            {
                var index = offset.material;
                if (index < 0 || index >= Materials.Length)
                    continue;

                var material = Materials[index];
                material.SetColor("_Color", Combine(_materialBaseDiffuse[index], offset.diffuse, offset.calcMode, weight));
                material.SetColor("_SpecTint", Combine(_materialBaseSpecular[index], offset.specular, offset.calcMode, weight)
                                              * Mathf.Clamp01(_materialBaseSpecularStrength[index] + offset.specularStrength * weight));
                material.SetColor("_AmbientColor", Combine(_materialBaseAmbient[index], offset.ambient, offset.calcMode, weight));
            }
        }

        public float BlushWeight
        {
            get => _blushMorphIndex >= 0 ? _blushWeight : 0f;
            set
            {
                _blushWeight = Mathf.Clamp01(value);
                SetMaterialMorphWeight(_blushMorphIndex, _blushWeight);
            }
        }

        float _blushWeight;

        public int BlushMaterialIndex => _blushMaterialIndex;

        static Color Combine(Color baseValue, float[] offset, int calcMode, float weight)
        {
            if (offset == null || offset.Length < 3)
                return baseValue;

            var a = offset.Length > 3 ? offset[3] : 1f;
            if (calcMode == 0)
            {
                // Multiplicative, interpolated towards the multiplier by weight.
                var r = Mathf.Lerp(1f, offset[0], weight);
                var g = Mathf.Lerp(1f, offset[1], weight);
                var b = Mathf.Lerp(1f, offset[2], weight);
                var alpha = Mathf.Lerp(1f, a, weight);
                return new Color(baseValue.r * r, baseValue.g * g, baseValue.b * b, baseValue.a * alpha);
            }

            return new Color(
                baseValue.r + offset[0] * weight,
                baseValue.g + offset[1] * weight,
                baseValue.b + offset[2] * weight,
                baseValue.a + a * weight);
        }
    }
}
