using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class VertexNormalViewer : MonoBehaviour
{
    [Header("线条长度设置")]
    [Tooltip("法线线条长度")]
    public float normalLength = 0.01f;
    
    [Tooltip("切线线条长度")]
    public float tangentLength = 0.01f;
    
    [Tooltip("副切线线条长度")]
    public float binormalLength = 0.01f;

    [Header("颜色设置")]
    public Color normalColor = Color.blue;
    public Color tangentColor = Color.green;
    public Color binormalColor = Color.red;

    [Header("其他设置")]
    [Tooltip("是否只在选中时显示")]
    public bool onlyShowWhenSelected = false;
    
    [Tooltip("每隔多少个顶点绘制（用于减少绘制数量）")]
    public int vertexStep = 1;
    
    [Tooltip("编辑模式下是否使用原始网格位置（用于未播放动画时）")]
    public bool useOriginalMeshInEditMode = true;
    
    [Tooltip("是否显示调试信息")]
    public bool showDebugInfo = false;

    private MeshFilter meshFilter;
    private SkinnedMeshRenderer skinnedMeshRenderer;
    private Mesh bakedMesh;

    private void Awake()
    {
        meshFilter = GetComponent<MeshFilter>();
        skinnedMeshRenderer = GetComponent<SkinnedMeshRenderer>();
        
        if (meshFilter == null && skinnedMeshRenderer == null)
        {
            Debug.LogWarning("VertexNormalViewer: 未找到MeshFilter或SkinnedMeshRenderer组件！");
        }
        
        if (skinnedMeshRenderer != null)
        {
            bakedMesh = new Mesh();
        }
    }

    private void OnDestroy()
    {
        if (bakedMesh != null)
        {
            Destroy(bakedMesh);
        }
    }

    private void OnDrawGizmos()
    {
        if (!onlyShowWhenSelected)
        {
            DrawVertexVectors();
        }
    }

    private void OnDrawGizmosSelected()
    {
        if (onlyShowWhenSelected)
        {
            DrawVertexVectors();
        }
    }

    private void DrawVertexVectors()
    {
        // 在编辑模式下重新获取组件（因为Awake可能不会在编辑模式下调用）
        if (skinnedMeshRenderer == null)
        {
            skinnedMeshRenderer = GetComponent<SkinnedMeshRenderer>();
        }
        
        if (meshFilter == null)
        {
            meshFilter = GetComponent<MeshFilter>();
        }

        // 优先使用SkinnedMeshRenderer
        if (skinnedMeshRenderer != null && skinnedMeshRenderer.sharedMesh != null)
        {
            // 确保SkinnedMeshRenderer已启用且GameObject处于活动状态
            if (skinnedMeshRenderer.enabled && skinnedMeshRenderer.gameObject.activeInHierarchy)
            {
                DrawSkinnedMeshVectors();
            }
            return;
        }

        // 回退到MeshFilter
        if (meshFilter != null && meshFilter.sharedMesh != null)
        {
            DrawStaticMeshVectors(meshFilter.sharedMesh, this.transform);
        }
    }

    private void DrawSkinnedMeshVectors()
    {
        Mesh sourceMesh = skinnedMeshRenderer.sharedMesh;
        Transform transform = this.transform;

        Vector3[] vertices;
        Vector3[] normals;
        Vector4[] tangents;

        // 判断是否在编辑模式
        bool isEditMode = !Application.isPlaying;
        bool hasBones = skinnedMeshRenderer.bones != null && skinnedMeshRenderer.bones.Length > 0;

        if (showDebugInfo)
        {
            Debug.Log($"VertexNormalViewer: 模式={(isEditMode ? "编辑" : "运行")}, 骨骼数量={skinnedMeshRenderer.bones?.Length ?? 0}");
        }

        if (isEditMode && useOriginalMeshInEditMode)
        {
            // 编辑模式下使用原始网格数据
            vertices = sourceMesh.vertices;
            normals = sourceMesh.normals;
            tangents = sourceMesh.tangents;
        }
        else
        {
            // 运行时使用BakeMesh
            if (bakedMesh == null)
            {
                bakedMesh = new Mesh();
            }

            try
            {
                skinnedMeshRenderer.BakeMesh(bakedMesh, true);
                vertices = bakedMesh.vertices;
                
                // BakeMesh可能不会正确计算法线和切线，使用原始网格的
                normals = sourceMesh.normals;
                tangents = sourceMesh.tangents;
            }
            catch (System.Exception e)
            {
                if (showDebugInfo)
                {
                    Debug.LogWarning($"VertexNormalViewer: BakeMesh失败 - {e.Message}，使用原始网格");
                }
                // 如果BakeMesh失败，回退到原始网格
                vertices = sourceMesh.vertices;
                normals = sourceMesh.normals;
                tangents = sourceMesh.tangents;
            }
        }

        int vertexCount = vertices.Length;

        for (int i = 0; i < vertexCount; i += vertexStep)
        {
            Vector3 vertexPos = transform.TransformPoint(vertices[i]);

            // 绘制法线（蓝色）
            if (i < normals.Length)
            {
                Vector3 normalWorld = transform.TransformDirection(normals[i]).normalized;
                Gizmos.color = normalColor;
                Gizmos.DrawLine(vertexPos, vertexPos + normalWorld * normalLength);
            }

            // 绘制切线（绿色）
            if (i < tangents.Length)
            {
                Vector3 tangentWorld = transform.TransformDirection(tangents[i]).normalized;
                Gizmos.color = tangentColor;
                Gizmos.DrawLine(vertexPos, vertexPos + tangentWorld * tangentLength);
            }

            // 绘制副切线（红色）
            if (i < normals.Length && i < tangents.Length)
            {
                Vector3 normalWorld = transform.TransformDirection(normals[i]).normalized;
                Vector3 tangentWorld = transform.TransformDirection(tangents[i]).normalized;
                float tangentW = tangents[i].w;
                Vector3 binormalWorld = Vector3.Cross(normalWorld, tangentWorld) * tangentW;
                
                Gizmos.color = binormalColor;
                Gizmos.DrawLine(vertexPos, vertexPos + binormalWorld * binormalLength);
            }
        }
    }

    private void DrawStaticMeshVectors(Mesh mesh, Transform transform)
    {
        Vector3[] vertices = mesh.vertices;
        Vector3[] normals = mesh.normals;
        Vector4[] tangents = mesh.tangents;

        int vertexCount = vertices.Length;

        for (int i = 0; i < vertexCount; i += vertexStep)
        {
            Vector3 vertexPos = transform.TransformPoint(vertices[i]);

            // 绘制法线（蓝色）
            if (i < normals.Length)
            {
                Vector3 normalWorld = transform.TransformDirection(normals[i]).normalized;
                Gizmos.color = normalColor;
                Gizmos.DrawLine(vertexPos, vertexPos + normalWorld * normalLength);
            }

            // 绘制切线（绿色）
            if (i < tangents.Length)
            {
                Vector3 tangentWorld = transform.TransformDirection(tangents[i]).normalized;
                Gizmos.color = tangentColor;
                Gizmos.DrawLine(vertexPos, vertexPos + tangentWorld * tangentLength);
            }

            // 绘制副切线（红色）
            if (i < normals.Length && i < tangents.Length)
            {
                Vector3 normalWorld = transform.TransformDirection(normals[i]).normalized;
                Vector3 tangentWorld = transform.TransformDirection(tangents[i]).normalized;
                float tangentW = tangents[i].w;
                Vector3 binormalWorld = Vector3.Cross(normalWorld, tangentWorld) * tangentW;
                
                Gizmos.color = binormalColor;
                Gizmos.DrawLine(vertexPos, vertexPos + binormalWorld * binormalLength);
            }
        }
    }
}
