using UnityEngine;

namespace UnityEngine.Rendering.Universal
{
    /// <summary>
    /// 阴影切片数据 - 存储单个阴影对象的渲染数据
    /// </summary>
    public struct PerObjectShadowSliceData
    {
        public Matrix4x4 viewMatrix;         // 视图矩阵（光源视角）
        public Matrix4x4 projectionMatrix;   // 投影矩阵（正交投影）
        public Matrix4x4 shadowTransform;    // 世界空间到阴影UV的变换矩阵
        public Matrix4x4 shadowToWorldMatrix; // 阴影空间到世界空间的变换矩阵（用于体积投影和裁剪）
        public int offsetX, offsetY;         // Tile在Atlas中的偏移（像素）
        public int resolution;               // Tile分辨率
        public Vector4 uvScaleOffset;        // UV缩放偏移 (xy=scale, zw=offset)

        public void Clear() { /* 重置为默认值 */ }
    }

    /// <summary>
    /// 阴影对象数据 - Pass中使用的运行时数据
    /// </summary>
    public class PerObjectShadowData
    {
        public PerObjectShadowProjector projector;  // 阴影投射器引用
        public PerObjectShadowSliceData mainSliceData;     // 主光源渲染切片数据
        public PerObjectShadowSliceData virtualSliceData;  // 虚拟光源渲染切片数据
        public bool isCulled;                       // 是否被剔除
    }

    /// <summary>
    /// PerObjectShadow 核心工具类
    /// 提供矩阵计算、Atlas 布局算法、Texel Snapping 以及视锥剔除功能
    /// </summary>
    public static class PerObjectShadowUtils
    {
        public const int k_MaxObjectsNum = 32;  // Atlas 支持的最大对象数

        // Atlas 布局采样顺序，采用分块模式优化 GPU 缓存命中率
        private static readonly int[] s_SliceArray = {
            0,  1,  4,  5,  16, 17, 20, 21,   
            2,  3,  6,  7,  18, 19, 22, 23,
            8,  9,  12, 13, 24, 25, 28, 29,
            10, 11, 14, 15, 26, 27, 30, 31,
        };
        /*视口坐标系（Y轴向上）:

y=1536┌────────┬────────┬────────┬────────┐
      │10,11   │14,15   │26,27   │30,31   │
y=1024├────────┼────────┼────────┼────────┤
      │8,9     │12,13   │24,25   │28,29   │
y=512 ├────────┼────────┼────────┼────────┤
      │2,3     │6,7     │18,19   │22,23   │
y=0   ├────────┼────────┼────────┼────────┤
      │0,1     │4,5     │16,17   │20,21   │ ← 数组第0行在底部
      └────────┴────────┴────────┴────────┘
        x=0     x=512   x=1024   x=1536*/

        #region 分辨率计算

        /// <summary>
        /// 根据Atlas尺寸和Tile数量，计算每个Tile的分辨率（逐级减半直到能容纳所有Tile）
        /// </summary>
        public static int GetPerObjectTileResolutionInAtlas(int atlasWidth, int atlasHeight, int tileCount)
        {
            int resolution = Mathf.Min(atlasWidth, atlasHeight);
            int currentTileCount = atlasWidth / resolution * atlasHeight / resolution;
            while (currentTileCount < tileCount)
            {
                resolution >>= 1;
                currentTileCount = atlasWidth / resolution * atlasHeight / resolution;
            }
            return resolution;
        }

        /// <summary>
        /// 根据对象数量动态调整Atlas分辨率（优化内存使用）
        /// </summary>
        public static Vector2Int GetPerObjectShadowMapResolution(int baseResolution, int tileCount)
        {
            Vector2Int resolution = new Vector2Int(baseResolution, baseResolution);
            if (tileCount == 2) resolution.y >>= 1;                    // 1x2布局
            else if (tileCount >= 5 && tileCount <= 8) resolution.x <<= 1;    // 2x4布局
            else if (tileCount >= 17 && tileCount <= 32) resolution.x <<= 1;  // 4x8布局
            return resolution;
        }
        
        /// <summary>
        /// 计算Tile在Atlas中的像素偏移
        /// </summary>
        public static Vector2Int ComputeSliceOffset(int tileIndex, int tileResolution)
        {
            int x = 0;
            for (; x < s_SliceArray.Length; x++)
                if (tileIndex == s_SliceArray[x]) break;

            return new Vector2Int(x % 8 * tileResolution, x / 8 * tileResolution);
        }
        
        /// <summary>
        /// 应用Atlas切片变换，将阴影坐标映射到对应Tile
        /// </summary>
        public static void ApplySliceTransform(ref PerObjectShadowSliceData shadowSliceData, int shadowmapWidth, int shadowmapHeight)
        {
            Matrix4x4 sliceTransform = Matrix4x4.identity;
            sliceTransform.m00 = (float)shadowSliceData.resolution / shadowmapWidth;   // X缩放
            sliceTransform.m11 = (float)shadowSliceData.resolution / shadowmapHeight;  // Y缩放
            sliceTransform.m03 = (float)shadowSliceData.offsetX / shadowmapWidth;      // X偏移
            sliceTransform.m13 = (float)shadowSliceData.offsetY / shadowmapHeight;     // Y偏移

            shadowSliceData.shadowTransform = sliceTransform * shadowSliceData.shadowTransform;
        }

        #endregion

        #region 矩阵计算

        /// <summary>
        /// 计算完整的阴影切片数据（矩阵+Atlas偏移+UV变换）- 使用具体旋转和位置
        /// </summary>
        public static void ExtractDirectionalLightMatrix(int tileIndex, Quaternion lightRotation, Vector3 lightPosition, Bounds boundsWS, 
            float farPlaneScale, int shadowmapWidth, int shadowmapHeight, int tileResolution, 
            out PerObjectShadowSliceData outSliceData)
        {
            ComputePerObjectShadowMatrices(lightRotation, boundsWS, farPlaneScale, tileResolution, out var viewMatrix, out var projMatrix);

            var sliceData = new PerObjectShadowSliceData();
            sliceData.viewMatrix = viewMatrix;
            sliceData.projectionMatrix = projMatrix;
            sliceData.shadowTransform = GetShadowTransform(projMatrix, viewMatrix);
            sliceData.shadowToWorldMatrix = (projMatrix * viewMatrix).inverse;//把“阴影裁剪空间里的单位立方体”变换成世界空间中的阴影体积盒，用于体积投影绘制（限制像素范围）

            Vector2Int offset = ComputeSliceOffset(tileIndex, tileResolution);
            sliceData.offsetX = offset.x;
            sliceData.offsetY = offset.y;
            sliceData.resolution = tileResolution;
            sliceData.uvScaleOffset = new Vector4(
                (float)tileResolution / shadowmapWidth, (float)tileResolution / shadowmapHeight,
                (float)offset.x / shadowmapWidth, (float)offset.y / shadowmapHeight);

            ApplySliceTransform(ref sliceData, shadowmapWidth, shadowmapHeight);

            outSliceData = sliceData;
        }

        /// <summary>
        /// 计算完整的阴影切片数据（矩阵+Atlas偏移+UV变换）- 使用平行光
        /// </summary>
        public static void ExtractDirectionalLightMatrix(int tileIndex, Light light, Bounds boundsWS, 
            float farPlaneScale, int shadowmapWidth, int shadowmapHeight, int tileResolution, 
            out PerObjectShadowSliceData outSliceData)
        {
            ExtractDirectionalLightMatrix(tileIndex, light.transform.rotation, light.transform.position, boundsWS, farPlaneScale, shadowmapWidth, shadowmapHeight, tileResolution, out outSliceData);
        }
        
        /// <summary>
        /// 计算自阴影专用矩阵：阴影相机视锥体会紧贴主相机视锥体与物体包围盒的交集，最大化分辨率利用率
        /// </summary>
        public static void ExtractSelfShadowMatrix(int tileIndex, Quaternion lightRotation, Vector3 lightPosition, Bounds boundsWS, 
            Camera mainCamera, float farPlaneScale, int shadowmapWidth, int shadowmapHeight, int tileResolution, float orthoSizeScale,
            out PerObjectShadowSliceData outSliceData)
        {
            // 1. 获取基础视图矩阵
            Vector3 lightForward = lightRotation * Vector3.forward;
            Vector3 lightUp = lightRotation * Vector3.up;
            // 视图矩阵以物体中心为参考，计算 Ortho 范围
            var lookMatrix = Matrix4x4.LookAt(boundsWS.center - lightForward * boundsWS.extents.magnitude, boundsWS.center, lightUp);
            var scaleMatrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(1, 1, -1));
            Matrix4x4 viewMatrix = scaleMatrix * lookMatrix.inverse;

            // 2. 计算视野交集中心
            // 我们取物体中心和相机视线前方一段距离的加权点，确保阴影相机焦点随相机移动
            float distanceToObj = Vector3.Distance(mainCamera.transform.position, boundsWS.center);
            Vector3 camLookAt = mainCamera.transform.position + mainCamera.transform.forward * Mathf.Min(distanceToObj, 2.0f);
            // 限制焦点不超出物体包围盒
            Vector3 focusPointWS = boundsWS.ClosestPoint(camLookAt);
            
            // 3. 动态调整 Ortho 范围
            // 离得越近，OrthoSize 越小，但要保证至少能包住一部分物体
            float orthoSize = Mathf.Clamp(distanceToObj * 0.6f, boundsWS.extents.magnitude * 0.2f, boundsWS.extents.magnitude);
            orthoSize *= Mathf.Max(0.0001f, orthoSizeScale);
            
            // 4. 在光源空间下进行像素对齐 (Texel Snapping)
            Vector3 focusPointLS = viewMatrix.MultiplyPoint3x4(focusPointWS);
            float worldTexelSize = (orthoSize * 2.0f) / tileResolution;
            
            float minX = focusPointLS.x - orthoSize;
            float minY = focusPointLS.y - orthoSize;
            // 对齐到像素单位
            minX = Mathf.Floor(minX / worldTexelSize) * worldTexelSize;
            minY = Mathf.Floor(minY / worldTexelSize) * worldTexelSize;
            float maxX = minX + orthoSize * 2.0f;
            float maxY = minY + orthoSize * 2.0f;

            // 5. 确保 Near/Far 足够包住整个物体，防止深度裁剪
            float zFar = 2.0f * boundsWS.extents.magnitude * farPlaneScale;
            Matrix4x4 projMatrix = Matrix4x4.Ortho(minX, maxX, minY, maxY, 0.0f, zFar);

            // 6. 输出数据
            var sliceData = new PerObjectShadowSliceData();
            sliceData.viewMatrix = viewMatrix;
            sliceData.projectionMatrix = projMatrix;
            sliceData.shadowTransform = GetShadowTransform(projMatrix, viewMatrix);
            sliceData.shadowToWorldMatrix = (projMatrix * viewMatrix).inverse;

            Vector2Int offset = ComputeSliceOffset(tileIndex, tileResolution);
            sliceData.offsetX = offset.x;
            sliceData.offsetY = offset.y;
            sliceData.resolution = tileResolution;
            sliceData.uvScaleOffset = new Vector4(
                (float)tileResolution / shadowmapWidth, (float)tileResolution / shadowmapHeight,
                (float)offset.x / shadowmapWidth, (float)offset.y / shadowmapHeight);

            ApplySliceTransform(ref sliceData, shadowmapWidth, shadowmapHeight);
            outSliceData = sliceData;
        }

        /// <summary>
        /// 计算阴影相机矩阵（视图+正交投影），视锥体刚好包住对象包围盒 - 使用具体旋转
        /// </summary>
        public static void ComputePerObjectShadowMatrices(Quaternion lightRotation, Bounds boundsWS, float farPlaneScale, int tileResolution,
            out Matrix4x4 viewMatrix, out Matrix4x4 projMatrix)
        {
            // 计算光源方向
            Vector3 lightForward = lightRotation * Vector3.forward;
            Vector3 lightUp = lightRotation * Vector3.up;

            // 1. 视图矩阵：看向包围盒中心
            float boxExtendLength = boundsWS.extents.magnitude;
            Vector3 shadowMapEye = boundsWS.center - lightForward * boxExtendLength;
            var lookMatrix = Matrix4x4.LookAt(shadowMapEye, boundsWS.center, lightUp);//求相机的世界矩阵camera to world
            var scaleMatrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(1, 1, -1));//将z轴翻转，对齐深度方向
            viewMatrix = scaleMatrix * lookMatrix.inverse;//求视图矩阵world to camera

            // 2. 将 AABB 的 8 个顶点变换到光源空间，计算紧凑的投影范围
            Vector3 center = boundsWS.center;
            Vector3 extents = boundsWS.extents;
            Vector3[] corners = {
                viewMatrix.MultiplyPoint3x4(center + new Vector3(extents.x, extents.y, extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(extents.x, extents.y, -extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(extents.x, -extents.y, extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(extents.x, -extents.y, -extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(-extents.x, extents.y, extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(-extents.x, extents.y, -extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(-extents.x, -extents.y, extents.z)),
                viewMatrix.MultiplyPoint3x4(center + new Vector3(-extents.x, -extents.y, -extents.z)),
            };//算出八个角点在光源相机空间下的坐标

            float minX = float.MaxValue, maxX = float.MinValue;
            float minY = float.MaxValue, maxY = float.MinValue;
            float minZ = float.MaxValue, maxZ = float.MinValue;
            for (int i = 0; i < 8; i++) {
                minX = Mathf.Min(minX, corners[i].x); maxX = Mathf.Max(maxX, corners[i].x);
                minY = Mathf.Min(minY, corners[i].y); maxY = Mathf.Max(maxY, corners[i].y);
                minZ = Mathf.Min(minZ, corners[i].z); maxZ = Mathf.Max(maxZ, corners[i].z);
            }//计算xyz的最大最小，确定正交投影的范围

            // 3. 像素对齐 (Texel Snapping)：防止阴影随相机移动而闪烁,对齐后，投影窗口只会以“一个 texel”为步长跳动，稳定很多。
            float orthoWidth = maxX - minX;
            float orthoHeight = maxY - minY;

            // 因为是非正方形投影（宽不等于高），X和Y方向的单个像素在世界空间中对应的长度是不同的！
            float worldTexelSizeX = orthoWidth / tileResolution;
            float worldTexelSizeY = orthoHeight / tileResolution;

            minX = Mathf.Floor(minX / worldTexelSizeX) * worldTexelSizeX;
            maxX = minX + orthoWidth;
            minY = Mathf.Floor(minY / worldTexelSizeY) * worldTexelSizeY;
            maxY = minY + orthoHeight;

            // 4. 构建投影矩阵 (确保 Near/Far 足够包住物体)
            float zFar = (maxZ - minZ) * 2.0f * farPlaneScale;
            projMatrix = Matrix4x4.Ortho(minX, maxX, minY, maxY, 0.0f, zFar);
        }

        /// <summary>
        /// 计算阴影相机矩阵（视图+正交投影），视锥体刚好包住对象包围盒
        /// </summary>
        public static void ComputePerObjectShadowMatrices(Light light, Bounds boundsWS, float farPlaneScale, int tileResolution,
            out Matrix4x4 viewMatrix, out Matrix4x4 projMatrix)
        {
            ComputePerObjectShadowMatrices(light.transform.rotation, boundsWS, farPlaneScale, tileResolution, out viewMatrix, out projMatrix);
        }

        /// <summary>
        /// 构建世界空间到阴影纹理空间的变换矩阵（-1~1 → 0~1）
        /// </summary>
        public static Matrix4x4 GetShadowTransform(Matrix4x4 proj, Matrix4x4 view)
        {
            // 处理Reversed Z
            if (SystemInfo.usesReversedZBuffer)
            {
                proj.m20 = -proj.m20; proj.m21 = -proj.m21;
                proj.m22 = -proj.m22; proj.m23 = -proj.m23;
            }

            Matrix4x4 worldToShadow = proj * view;

            // 缩放偏移矩阵：[-1,1] → [0,1]，从 NDC 空间 [-1, 1] 映射到 纹理采样空间 [0, 1] ，方便用来采样阴影贴图
            var scaleBias = Matrix4x4.identity;
            scaleBias.m00 = scaleBias.m11 = scaleBias.m22 = 0.5f;
            scaleBias.m03 = scaleBias.m13 = scaleBias.m23 = 0.5f;

            return scaleBias * worldToShadow;
        }

        #endregion

        #region 阴影渲染

        private static Mesh s_ShadowProjectorMesh;
        /// <summary>
        /// 获取用于体积投影的单位立方体网格
        /// </summary>
        public static Mesh shadowProjectorMesh
        {
            get
            {
                if (s_ShadowProjectorMesh == null)
                    s_ShadowProjectorMesh = CoreUtils.CreateCubeMesh(new Vector3(-1, -1, -1), new Vector3(1, 1, 1));
                return s_ShadowProjectorMesh;
            }
        }

        /// <summary>
        /// 计算阴影偏移参数（消除Shadow Acne和Peter Panning）
        /// </summary>
        public static Vector4 GetShadowBias(Light shadowLight, float rawDepthBias, float rawNormalBias, 
            Matrix4x4 lightProjectionMatrix, float shadowResolution)
        {
            float frustumSize = 2.0f / lightProjectionMatrix.m00;// 计算阴影相机视窗尺寸，从矩阵反推，等同2 * boxExtendLength
            float texelSize = frustumSize / shadowResolution;// 得出每个像素的尺寸
            float depthBias = -rawDepthBias * texelSize;   // 深度偏移（解决Acne）
            float normalBias = -rawNormalBias * texelSize; // 法线偏移（解决Peter Panning）

            return new Vector4(depthBias, normalBias, 0.0f, 0.0f);
        }

        /// <summary>
        /// 设置ShadowCaster Pass所需的Shader全局变量 - 使用具体旋转和位置
        /// </summary>
        public static void SetupShadowCasterConstantBuffer(CommandBuffer cmd, Quaternion lightRotation, Vector3 lightPosition, Vector4 shadowBias)
        {
            Vector3 lightForward = lightRotation * Vector3.forward;
            cmd.SetGlobalVector("_ShadowBias", shadowBias);
            cmd.SetGlobalVector("_LightDirection", new Vector4(-lightForward.x, -lightForward.y, -lightForward.z, 0.0f));
            cmd.SetGlobalVector("_LightPosition", new Vector4(lightPosition.x, lightPosition.y, lightPosition.z, 1.0f));
        }

        /// <summary>
        /// 设置ShadowCaster Pass所需的Shader全局变量
        /// </summary>
        public static void SetupShadowCasterConstantBuffer(CommandBuffer cmd, Light shadowLight, Vector4 shadowBias)
        {
            SetupShadowCasterConstantBuffer(cmd, shadowLight.transform.rotation, shadowLight.transform.position, shadowBias);
        }

        /// <summary>
        /// 渲染单个阴影切片到Atlas
        /// </summary>
        public static void RenderShadowSlice(CommandBuffer cmd, Renderer[] renderers, 
            ref PerObjectShadowSliceData shadowSliceData, Material material, int passIndex)
        {
            // 设置视口到对应Tile区域
            cmd.SetViewport(new Rect(shadowSliceData.offsetX, shadowSliceData.offsetY, 
                shadowSliceData.resolution, shadowSliceData.resolution));
            cmd.SetViewProjectionMatrices(shadowSliceData.viewMatrix, shadowSliceData.projectionMatrix);

            if (renderers == null || renderers.Length == 0)
                return;

            Renderer r = null;
            for (int i = 0; i < renderers.Length; i++)
            {
                if (renderers[i] != null)
                {
                    r = renderers[i];
                    break;
                }
            }

            if (r == null)
                return;

            cmd.DrawRenderer(r, material, 0, passIndex);
        }

        #endregion

        #region 剔除

        /// <summary>
        /// 计算视锥剔除球（用于判断阴影是否可能在相机视野内）
        /// </summary>
        public static void ComputeCullingSphere(Light light, Bounds boundsWS, float farPlaneScale,
            out Vector3 sphereCenter, out float sphereRadius)
        {
            Vector3 boxCenter = boundsWS.center;
            float boxExtendLength = boundsWS.extents.magnitude;

            // 阴影相机位置和远平面
            Vector3 shadowMapEye = boxCenter - light.transform.forward * boxExtendLength;
            float zFar = 2.0f * boxExtendLength * farPlaneScale;

            // 剔除球中心在阴影相机中点，半径覆盖整个视锥体
            Vector3 cullingBoxNearTL = shadowMapEye - light.transform.right * boxExtendLength + light.transform.up * boxExtendLength;
            sphereCenter = shadowMapEye + zFar * 0.5f * light.transform.forward;
            sphereRadius = Vector3.Distance(cullingBoxNearTL, sphereCenter);
        }

        /// <summary>
        /// 视锥-球体剔除（返回true表示被剔除）
        /// </summary>
        public static bool FrustumSphereCulling(Plane[] frustumPlanes, Vector3 sphereCenter, float sphereRadius)
        {
            for (int i = 0; i < 6; i++)
            {// Ax + By + Cz + D = 0
                float d = Vector3.Dot(sphereCenter, frustumPlanes[i].normal);
                if (frustumPlanes[i].distance + d + sphereRadius < 0)
                    return true;  // 球体完全在视锥外
            }
            return false;
        }

        #endregion
    }
}
