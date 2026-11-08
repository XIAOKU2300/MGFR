using UnityEngine;
using System.Collections.Generic;

/// <summary>毛发惯性延迟组件 - 模拟毛发在运动时的"甩动"效果</summary>
[RequireComponent(typeof(Renderer))]
public class FurInertia : MonoBehaviour
{
    public enum MotionSource { Transform, Bones }

    [Header("运动源")]
    [Tooltip("Transform: 追踪整体移动\nBones: 追踪骨骼动画")]
    public MotionSource motionSource = MotionSource.Transform;

    [Tooltip("骨骼数组（右键菜单\"检测Fur骨骼并保存\"自动填充）")]
    public Transform[] bones;

    [Header("惯性参数")]
    [Range(1f, 20f)][Tooltip("跟随速度，值越大毛发越\"硬\"")]
    public float followSpeed = 5f;
    
    [Range(0.1f, 2f)][Tooltip("阻尼系数，值越大越快停止")]
    public float damping = 0.5f;
    
    [Range(0f, 2f)][Tooltip("旋转惯性强度")]
    public float rotationInfluence = 1f;
    
    [Range(0f, 2f)][Tooltip("移动惯性强度")]
    public float movementInfluence = 1f;
    
    [Range(0f, 2f)][Tooltip("整体强度缩放")]
    public float inertiaIntensity = 1f;

    [Header("旋转惯性参数")]
    [Tooltip("毛发平均高度，影响Pitch/Roll甩动幅度")]
    public float assumedFurHeight = 0.1f;
    
    [Tooltip("毛发平均水平半径，影响Yaw甩动幅度")]
    public float assumedFurRadius = 0.1f;

    private Vector3 _prevPosition;
    private Quaternion _prevRotation;
    private Vector3 _delayedOffset;
    private Vector3 _delayedVelocity;

    private static readonly int _FurInertiaOffsetID = Shader.PropertyToID("_FurInertiaOffset");
    private static readonly int _FurInertiaIntensityID = Shader.PropertyToID("_FurInertiaIntensity");

    private MaterialPropertyBlock _propBlock;
    private Renderer _renderer;

    /// <summary>重置惯性状态，避免从旧数据继续计算产生跳跃</summary>
    void ResetState()
    {
        if (motionSource == MotionSource.Bones && bones != null && bones.Length > 0)
        {
            _prevPosition = GetBonesCenterPosition();
            _prevRotation = GetBonesCenterRotation();
        }
        else
        {
            _prevPosition = transform.position;
            _prevRotation = transform.rotation;
        }
        _delayedOffset = Vector3.zero;
        _delayedVelocity = Vector3.zero;
    }

    /// <summary>初始化渲染组件，骨骼模式自动检测骨骼</summary>
    void Start()
    {
        _renderer = GetComponent<Renderer>();
        _propBlock = new MaterialPropertyBlock();

        // 运行时如果 bones 已有值（编辑器预设），直接使用；否则尝试自动检测
        if (motionSource == MotionSource.Bones && (bones == null || bones.Length == 0))
        {
            var smr = GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr != null && smr.bones != null && smr.bones.Length > 0)
                bones = smr.bones;
        }
        ResetState();
    }

    /// <summary>自动检测受Fur材质影响的骨骼（编辑器专用）</summary>
    Transform[] DetectFurBones(SkinnedMeshRenderer smr)
    {
        Mesh mesh = smr.sharedMesh;
        if (mesh == null) return smr.bones;

        // 1. 找出使用Fur材质的subMesh索引
        HashSet<int> furSubMeshIndices = new HashSet<int>();
        Material[] materials = smr.sharedMaterials;

        for (int i = 0; i < materials.Length && i < mesh.subMeshCount; i++)
        {
            if (materials[i] != null && IsFurMaterial(materials[i]))
                furSubMeshIndices.Add(i);
        }

        if (furSubMeshIndices.Count == 0) return smr.bones;

        // 2. 收集这些subMesh使用的顶点索引
        HashSet<int> furVertexIndices = new HashSet<int>();
        foreach (int subMeshIdx in furSubMeshIndices)
        {
            int[] triangles = mesh.GetTriangles(subMeshIdx);
            foreach (int idx in triangles)
                furVertexIndices.Add(idx);
        }

        // 3. 通过boneWeights找出相关骨骼索引
        BoneWeight[] boneWeights = mesh.boneWeights;
        HashSet<int> furBoneIndices = new HashSet<int>();
        Transform[] smrBones = smr.bones;

        foreach (int vertIdx in furVertexIndices)
        {
            if (vertIdx >= boneWeights.Length) continue;
            BoneWeight bw = boneWeights[vertIdx];

            if (bw.weight0 > 0.001f) furBoneIndices.Add(bw.boneIndex0);
            if (bw.weight1 > 0.001f) furBoneIndices.Add(bw.boneIndex1);
            if (bw.weight2 > 0.001f) furBoneIndices.Add(bw.boneIndex2);
            if (bw.weight3 > 0.001f) furBoneIndices.Add(bw.boneIndex3);
        }

        // 4. 转换为骨骼Transform数组
        List<Transform> result = new List<Transform>(furBoneIndices.Count);
        foreach (int boneIdx in furBoneIndices)
        {
            if (boneIdx >= 0 && boneIdx < smrBones.Length && smrBones[boneIdx] != null)
                result.Add(smrBones[boneIdx]);
        }

        return result.Count > 0 ? result.ToArray() : smr.bones;
    }

    /// <summary>判断材质是否为Fur材质</summary>
    bool IsFurMaterial(Material mat)
    {
        if (mat == null) return false;
        string shaderName = mat.shader?.name?.ToLower() ?? "";
        string matName = mat.name?.ToLower() ?? "";
        return shaderName.Contains("fur") || matName.Contains("fur");
    }

#if UNITY_EDITOR
    [ContextMenu("检测Fur骨骼并保存")]
    void DetectAndSaveFurBones()
    {
        var smr = GetComponentInChildren<SkinnedMeshRenderer>();
        if (smr == null)
        {
            Debug.LogError($"[FurInertia] {name}: 未找到 SkinnedMeshRenderer");
            return;
        }

        var detected = DetectFurBones(smr);
        bones = detected;
        UnityEditor.EditorUtility.SetDirty(this);

        Debug.Log($"[FurInertia] {name}: 已保存 {bones.Length}/{smr.bones.Length} 根Fur骨骼");
        for (int i = 0; i < bones.Length && i < 10; i++)
            Debug.Log($"  [{i}] {bones[i]?.name ?? "null"}");
        if (bones.Length > 10) Debug.Log($"  ... 共{bones.Length}根");
    }

    [ContextMenu("清除已保存的骨骼")]
    void ClearSavedBones()
    {
        bones = null;
        UnityEditor.EditorUtility.SetDirty(this);
        Debug.Log($"[FurInertia] {name}: 已清除骨骼数据");
    }
#endif

    /// <summary>每次启用组件时重置状态</summary>
    void OnEnable() => ResetState();

    /// <summary>计算骨骼中心平均位置，用于骨骼模式追踪整体移动</summary>
    Vector3 GetBonesCenterPosition()
    {
        if (bones == null || bones.Length == 0) return transform.position;
        Vector3 center = Vector3.zero;
        int count = 0;
        for (int i = 0; i < bones.Length; i++)
            if (bones[i] != null) { center += bones[i].position; count++; }
        return count > 0 ? center / count : transform.position;
    }

    /// <summary>获取骨骼代表性旋转，使用第一个有效骨骼的旋转</summary>
    Quaternion GetBonesCenterRotation()
    {
        if (bones == null || bones.Length == 0) return transform.rotation;
        for (int i = 0; i < bones.Length; i++)
            if (bones[i] != null) return bones[i].rotation;
        return transform.rotation;
    }

    /// <summary>每帧惯性计算核心逻辑，在所有动画更新后执行</summary>
    void LateUpdate()
    {
        // 获取当前状态
        Vector3 currentPosition;
        Quaternion currentRotation;
        if (motionSource == MotionSource.Bones && bones != null && bones.Length > 0)
        {
            currentPosition = GetBonesCenterPosition();
            currentRotation = GetBonesCenterRotation();
        }
        else
        {
            currentPosition = transform.position;
            currentRotation = transform.rotation;
        }

        float dt = Time.deltaTime;
        if (dt < 0.001f) { _prevPosition = currentPosition; _prevRotation = currentRotation; return; }

        // 计算线速度和角速度
        Vector3 linearVelocity = (currentPosition - _prevPosition) / dt;
        
        Quaternion rotationDelta = currentRotation * Quaternion.Inverse(_prevRotation);
        rotationDelta.ToAngleAxis(out float angle, out Vector3 axis);
        Vector3 angularVelocity = axis * (angle * Mathf.Deg2Rad) / dt;

        // 计算旋转惯性：毛发顶端线速度 = 角速度 × 毛发位置
        Vector3 localAngVel = transform.InverseTransformDirection(angularVelocity);
        Vector3 localInertia = new Vector3(
            localAngVel.z * assumedFurHeight - localAngVel.y * assumedFurRadius,
            0,
            -localAngVel.x * assumedFurHeight
        );
        Vector3 angularInertia = transform.TransformDirection(localInertia) * rotationInfluence;

        // 目标偏移 = 移动惯性（取负）+ 旋转惯性
        Vector3 targetOffset = (-linearVelocity * movementInfluence + angularInertia) * inertiaIntensity;

        // 平滑跟随 + 阻尼衰减
        _delayedOffset = Vector3.SmoothDamp(_delayedOffset, targetOffset, ref _delayedVelocity, 1f / followSpeed, Mathf.Infinity, dt);
        _delayedOffset *= (1f - damping * dt);

        // 更新历史状态
        _prevPosition = currentPosition;
        _prevRotation = currentRotation;

        // 传递给Shader
        _renderer.GetPropertyBlock(_propBlock);
        _propBlock.SetVector(_FurInertiaOffsetID, _delayedOffset);
        _propBlock.SetFloat(_FurInertiaIntensityID, _delayedOffset.magnitude);
        _renderer.SetPropertyBlock(_propBlock);
    }

    /// 公开接口：重置惯性状态（传送、重生等场景调用）
    public void ResetInertia() => ResetState();
}
