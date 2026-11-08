using System.Collections.Generic;
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
using System.IO;
#endif

[ExecuteAlways]
public class SmoothNormals : MonoBehaviour
{
    private SkinnedMeshRenderer[] _skinnedMeshRenderers;
    private MeshFilter[] _meshFilters;

    private struct WeightedNormal
    {
        public Vector3 normal;
        public float weight;
    }

    private void OnEnable()
    {
        RefreshComponents();
    }

    private void RefreshComponents()
    {
        _skinnedMeshRenderers = GetComponentsInChildren<SkinnedMeshRenderer>();
        _meshFilters = GetComponentsInChildren<MeshFilter>();
    }

    [ContextMenu("Generate and Save Smooth Normals")]
    public void GenerateSmoothNormals()
    {
        RefreshComponents();
        
#if UNITY_EDITOR
        HashSet<string> pathsToReimport = new HashSet<string>();

        // 处理 SkinnedMeshRenderer
        foreach (var smr in _skinnedMeshRenderers)
        {
            if (smr != null && smr.sharedMesh != null)
            {
                MarkForSmoothNormals(smr.sharedMesh, pathsToReimport);
            }
        }

        // 处理 MeshFilter
        foreach (var mf in _meshFilters)
        {
            if (mf != null && mf.sharedMesh != null)
            {
                MarkForSmoothNormals(mf.sharedMesh, pathsToReimport);
            }
        }
        
        if (pathsToReimport.Count > 0)
        {
            foreach(var path in pathsToReimport)
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                Debug.Log($"已重新导入并注入平滑法线: {path}");
            }
            Debug.Log("平滑法线处理完毕，已直接写入FBX源数据。");
        }
        else
        {
            Debug.Log("没有需要处理的FBX文件，或者它们已经被标记过了。");
        }
#endif
    }

#if UNITY_EDITOR
    private void MarkForSmoothNormals(Mesh mesh, HashSet<string> pathsToReimport)
    {
        string path = AssetDatabase.GetAssetPath(mesh);
        if (!string.IsNullOrEmpty(path) && (path.ToLower().EndsWith(".fbx") || path.ToLower().EndsWith(".obj")))
        {
            ModelImporter importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer != null && !importer.userData.Contains("SmoothNormals_True"))
            {
                importer.userData += "SmoothNormals_True;";
                pathsToReimport.Add(path);
            }
        }
    }
#endif

    // Start is called before the first frame update
    void Start()
    {
        // 运行时不再需要执行，因为法线已经直接烘焙进FBX源文件了
    }

    public static void ApplySmoothNormals(Mesh mesh)
    {
        if (mesh == null) return;
        
        //创建一个字典，存顶点-顶点所有法线的键值对，顶点由唯一的Vector3来确定
        var normalDict = new Dictionary<Vector3, List<WeightedNormal>>();
        var triangles = mesh.triangles;
        var vertices = mesh.vertices;
        var normals = mesh.normals;
        var tangents = mesh.tangents;

        if (tangents == null || tangents.Length == 0)
        {
            Debug.LogWarning($"{mesh.name} 缺少切线信息，无法计算切线空间下的平滑法线。");
            return;
        }

        var smoothNormals = new Vector3[vertices.Length];
        //三角形个数为triangles数组的长度/3
        var n = triangles.Length / 3;
        for (var i = 0; i < n; i++)
        {
            //第i个三角形的三个顶点的索引分别是i*3,i*3+1,i*3=2
            var vertexIndices = new[] {triangles[i * 3], triangles[i * 3 + 1], triangles[i * 3 + 2]};
            for (var j = 0; j < 3; j++)
            {
                var vertexIndex = vertexIndices[j];
                var vertexPosition = vertices[vertexIndex];
                if (!normalDict.ContainsKey(vertexPosition))
                {
                    normalDict.Add(vertexPosition, new List<WeightedNormal>());
                }

                WeightedNormal weightedNormal;
                weightedNormal.normal = normals[vertexIndex];
                //获取当前顶点出发的两条边
                var lineA = Vector3.zero;
                var lineB = Vector3.zero;
                if (j == 0)
                {
                    lineA = vertices[vertexIndices[1]] - vertexPosition;
                    lineB = vertices[vertexIndices[2]] - vertexPosition;
                }
                else if (j == 1)
                {
                    lineA = vertices[vertexIndices[0]] - vertexPosition;
                    lineB = vertices[vertexIndices[2]] - vertexPosition;
                }
                else if (j == 2)
                {
                    lineA = vertices[vertexIndices[0]] - vertexPosition;
                    lineB = vertices[vertexIndices[1]] - vertexPosition;
                }
                //把角度作为权重，记录起来，
                var angle = Vector3.Angle(lineA, lineB) * Mathf.Deg2Rad;
                weightedNormal.weight = angle;
                normalDict[vertexPosition].Add(weightedNormal);
            }
        }

        for (var index = 0; index < vertices.Length; index++)
        {
            var vertex = vertices[index];
            var weightedNormalList = normalDict[vertex];
            var smoothNormal = Vector3.zero;
            float weightSum = 0;
            foreach (var weightedNormal in weightedNormalList)
            {
                weightSum += weightedNormal.weight;
            }

            foreach (var weightedNormal in weightedNormalList)
            {
                smoothNormal = smoothNormal + weightedNormal.normal * weightedNormal.weight / weightSum;
            }

            smoothNormal = smoothNormal.normalized;
            //构建三个正交向量，作为切线空间的坐标轴
            var normal = normals[index];
            var tangent = tangents[index];
            var biTangent = (Vector3.Cross(normal, (Vector3)tangent) * tangent.w).normalized;
            //构建TBN矩阵
            var tbn = new Matrix4x4(tangent, biTangent, normal, Vector4.zero);
            //相当于smoothNormal重新投影到三个坐标轴上，获取在切线空间下的法线。
            smoothNormals[index] = tbn.transpose.MultiplyVector(smoothNormal).normalized;
        }

        mesh.SetUVs(7, smoothNormals);
        Debug.Log($"平滑法线成功: {mesh.name}");
    }

    // Update is called once per frame
    void Update()
    {
    }
}

#if UNITY_EDITOR
public class SmoothNormalsPostprocessor : AssetPostprocessor
{
    void OnPostprocessModel(GameObject g)
    {
        ModelImporter importer = assetImporter as ModelImporter;
        // 检查FBX是否被标记了需要注入平滑法线
        if (importer != null && importer.userData.Contains("SmoothNormals_True"))
        {
            // 遍历并处理所有网格
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh != null)
                {
                    SmoothNormals.ApplySmoothNormals(mf.sharedMesh);
                }
            }
            
            foreach (var smr in g.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                if (smr.sharedMesh != null)
                {
                    SmoothNormals.ApplySmoothNormals(smr.sharedMesh);
                }
            }
        }
    }
}
#endif