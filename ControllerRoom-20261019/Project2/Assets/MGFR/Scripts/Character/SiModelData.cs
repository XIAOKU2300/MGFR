using System;

namespace MGFR.Character
{
    /// <summary>
    /// C# mirror of <c>converted/si/si_model.json</c>.
    ///
    /// These classes exist so <see cref="UnityEngine.JsonUtility"/> can read the
    /// converter's output without a JSON dependency. That constrains the shape:
    /// every type must be a plain <c>[Serializable]</c> class with public fields,
    /// no dictionaries, no properties, no interfaces. The converter writes exactly
    /// these names, so if a field is renamed in one place it must be renamed in
    /// both — <see cref="SiCharacterLoader"/> fails loudly rather than silently
    /// producing an empty character when the counts come back as zero.
    /// </summary>
    [Serializable]
    public sealed class SiModelData
    {
        public int formatVersion;
        public string generatedBy;
        public SiSourceInfo source;
        public float unitScale;
        public string coordinateNote;
        public SiCounts counts;
        public SiBounds boundsScaled;
        public SiTexture[] textures;
        public SiMaterial[] materials;
        public SiBone[] bones;
        public SiBlendShape[] blendShapes;
        public SiMaterialMorph[] materialMorphs;
        public SiRuntimeHints runtimeHints;
    }

    [Serializable]
    public sealed class SiSourceInfo
    {
        public string pmx;
        public string modelName;
        public string modelNameEn;
        public string comment;
    }

    [Serializable]
    public sealed class SiCounts
    {
        public int vertices;
        public int indices;
        public int bones;
        public int materials;
        public int textures;
        public int blendShapes;
        public int materialMorphs;
    }

    [Serializable]
    public sealed class SiBounds
    {
        public float[] min;
        public float[] max;
    }

    [Serializable]
    public sealed class SiTexture
    {
        public int index;
        /// <summary>The path as written in the PMX, which is not always where the file is.</summary>
        public string declared;
        /// <summary>How it was found: "declared path", "other tex/ fallback", ...</summary>
        public string route;
        public string file;
        public int bytes;
    }

    [Serializable]
    public sealed class SiMaterial
    {
        public int index;
        public string name;
        public string nameEn;
        public int texture;
        public string textureFile;
        public float[] diffuse;
        public float[] specular;
        public float specularStrength;
        public float[] ambient;
        public int drawFlags;
        public bool isTwoSided;
        public float[] edgeColor;
        public float edgeSize;
        public int sphereMode;
        public bool sharedToon;
        public int toonIndex;
        public int faceIndexCount;
        public int indexStart;
    }

    [Serializable]
    public sealed class SiBone
    {
        public int index;
        public string name;
        public string nameEn;
        /// <summary>-1 for a root bone.</summary>
        public int parent;
        /// <summary>Absolute position in model space, metres. Used for the bind pose.</summary>
        public float[] positionScaled;
        /// <summary>Offset from the parent, metres. This is what localPosition takes.</summary>
        public float[] localScaled;
        public int deformLayer;
        public bool isIk;
        public int inheritParent;
        public float inheritWeight;
    }

    [Serializable]
    public sealed class SiBlendShape
    {
        /// <summary>Index into the PMX morph list, for traceability only.</summary>
        public int index;
        public string name;
        public string nameEn;
        public int panel;
        public string classification;
        public int vertexCount;
    }

    [Serializable]
    public sealed class SiMaterialMorph
    {
        public int index;
        public string name;
        public int panel;
        public string classification;
        public SiMaterialOffset[] offsets;
    }

    [Serializable]
    public sealed class SiMaterialOffset
    {
        public int material;
        /// <summary>0 multiplies the base value, 1 adds to it.</summary>
        public int calcMode;
        public float[] diffuse;
        public float[] specular;
        public float specularStrength;
        public float[] ambient;
        public float[] edgeColor;
        public float edgeSize;
        public float[] textureTint;
        public float[] sphereTint;
        public float[] toonTint;
    }

    [Serializable]
    public sealed class SiRuntimeHints
    {
        public string[] vowelShapes;
        public string blinkShape;
        public string closedMouthShape;
        public string blushMaterialMorph;
    }
}
