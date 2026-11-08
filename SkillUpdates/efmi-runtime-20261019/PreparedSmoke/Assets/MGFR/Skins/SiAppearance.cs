using System;
using UnityEngine;

namespace MGFR.Character
{
    // Runtime resources only. Applying an appearance keeps the live bone objects,
    // character placement, speech/attention components and physics world alive.
    public sealed class SiAppearance
    {
        public string Id;
        public string DataRoot;
        public SiModelData Data;
        public Mesh Mesh;
        public Material[] Materials;

        public void ValidateAgainst(SiModelData live)
        {
            if (Data == null || Mesh == null || Materials == null ||
                Data.bones.Length != live.bones.Length ||
                Data.blendShapes.Length != live.blendShapes.Length ||
                Materials.Length != live.materials.Length ||
                Mesh.bindposes.Length != Data.bones.Length)
                throw new InvalidOperationException("Skin mesh/rig/material contract does not match Si.");
            for (int i = 0; i < live.bones.Length; i++)
                if (Data.bones[i].name != live.bones[i].name || Data.bones[i].parent != live.bones[i].parent)
                    throw new InvalidOperationException("Skin bone contract differs at " + i);
            for (int i = 0; i < live.blendShapes.Length; i++)
                if (Data.blendShapes[i].name != live.blendShapes[i].name)
                    throw new InvalidOperationException("Skin expression contract differs at " + i);
            for (int i = 0; i < live.materials.Length; i++)
                if (Data.materials[i].name != live.materials[i].name)
                    throw new InvalidOperationException("Skin material contract differs at " + i);
        }
    }
}
