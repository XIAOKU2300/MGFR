using System.Collections.Generic;
using UnityEngine;

namespace UnityEngine.Rendering.Universal
{
    /// <summary>
    /// PerObjectShadow Projector 组件
    /// 挂载在需要投射阴影的对象上，负责收集渲染器并计算包围盒
    /// </summary>
    [ExecuteAlways]
    [AddComponentMenu("Rendering/PerObjectShadow Projector")]
    public class PerObjectShadowProjector : MonoBehaviour
    {
        #region 序列化字段

        [SerializeField] private Renderer[] m_Renderers;           // 投射阴影的渲染器列表
        [SerializeField, HideInInspector] private Material m_ShadowMaterial = null; // 阴影材质
        [SerializeField] private Transform m_StencilRendererRoot;  // 标记 Stencil 的根节点
        [SerializeField] private Renderer[] m_StencilRenderers;    // 标记 Stencil 的渲染器列表

        #endregion

        #region 静态管理

        private static List<PerObjectShadowProjector> s_ActiveProjectors = new List<PerObjectShadowProjector>();
        

        private static Material s_DefaultShadowMaterial;
        public static Material defaultShadowMaterial
        {
            get
            {
                if (s_DefaultShadowMaterial == null)
                {
                    Shader shader = Shader.Find("Hidden/PerObjectShadowCaster");
                    if (shader != null)
                        s_DefaultShadowMaterial = new Material(shader);
                }
                return s_DefaultShadowMaterial;
            }
        }

        #endregion

        #region 公开属性

        public Renderer[] childRenderers => m_Renderers;
        public Material shadowMaterial => m_ShadowMaterial != null ? m_ShadowMaterial : defaultShadowMaterial;
        public int stencilRef => m_StencilRef; // 自动分配的 Stencil ID，用于体积裁剪时的对象过滤
        public static List<PerObjectShadowProjector> activeProjectors => s_ActiveProjectors;

        private static int s_NextStencilRef = 2;
        private int m_StencilRef = 0;
        private MaterialPropertyBlock m_StencilMPB;
        private Dictionary<Renderer, Material[]> m_OriginalSharedMaterials;
        private Dictionary<Material, Material> m_ClonedMaterials;
        private List<Material> m_OwnedMaterials;

        private Bounds m_CachedBounds;
        private bool m_BoundsDirty = true;
        private bool m_LastUseColliderBounds = true;

        /// <summary>
        /// 获取物体在世界空间下的合并包围盒
        /// </summary>
        public Bounds GetBounds(bool useColliderBounds)
        {
            if (m_BoundsDirty || transform.hasChanged || m_LastUseColliderBounds != useColliderBounds)
            {
                m_CachedBounds = CalculateBounds(useColliderBounds);
                m_BoundsDirty = false;
                transform.hasChanged = false;
                m_LastUseColliderBounds = useColliderBounds;
            }
            return m_CachedBounds;
        }

        private Bounds CalculateBounds(bool useColliderBounds)
        {
            // 1. 优先尝试使用碰撞体的物理包围盒（最准确、最紧凑，不会因为骨骼动画膨胀）
            if (useColliderBounds)
            {
                Collider collider = GetComponentInParent<Collider>();
                if (collider != null)
                {
                    return collider.bounds;
                }
            }

            // 2. 如果没有碰撞体，则退而求其次，遍历合并所有 Renderer 的包围盒
            if (m_Renderers == null || m_Renderers.Length == 0)
                return new Bounds(transform.position, Vector3.zero);

            Bounds combinedBounds = new Bounds(transform.position, Vector3.zero);
            bool initialized = false;

            foreach (var renderer in m_Renderers)
            {
                if (renderer == null) continue;

                if (!initialized)
                {
                    combinedBounds = renderer.bounds;
                    initialized = true;
                }
                else
                {
                    combinedBounds.Encapsulate(renderer.bounds);
                }
            }

            return combinedBounds;
        }

        #endregion

        #region Unity 生命周期

        void OnEnable()
        {
            if (!s_ActiveProjectors.Contains(this))
                s_ActiveProjectors.Add(this);

#if UNITY_EDITOR
            UnityEditor.EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
#endif

            if (m_StencilRef == 0)
            {
                m_StencilRef = s_NextStencilRef;
                s_NextStencilRef = (s_NextStencilRef % 255) + 1;
                if (s_NextStencilRef == 1) s_NextStencilRef = 2; // 保留1给环境分类
            }

            if (m_Renderers == null || m_Renderers.Length == 0)
                CollectRenderers();

            if ((m_StencilRenderers == null || m_StencilRenderers.Length == 0) && m_StencilRendererRoot != null)
                CollectStencilRenderers();

            ApplyStencilRefToRenderers();
        }

        void OnDisable()
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.playModeStateChanged -= OnPlayModeStateChanged;
#endif
            s_ActiveProjectors.Remove(this);
            CleanupStencilMaterials();
        }

#if UNITY_EDITOR
        void OnValidate()
        {
            if (!isActiveAndEnabled)
                return;

            // OnValidate can be called frequently. We clean up previous clones before applying new ones.
            CleanupStencilMaterials();

            if (Application.isPlaying)
            { 
                if ((m_StencilRenderers == null || m_StencilRenderers.Length == 0) && m_StencilRendererRoot != null)
                    CollectStencilRenderers();
                else
                    ApplyStencilRefToRenderers();
            }
            else
            {
                if (m_Renderers == null || m_Renderers.Length == 0)
                    CollectRenderers();
            }
        }

        private void OnPlayModeStateChanged(UnityEditor.PlayModeStateChange state)
        {
            // Before entering Play Mode, restore original materials to prevent scene pollution
            if (state == UnityEditor.PlayModeStateChange.ExitingEditMode)
            {
                CleanupStencilMaterials();
            }
            // After exiting Play Mode, re-apply stencil for editor preview
            else if (state == UnityEditor.PlayModeStateChange.EnteredEditMode)
            {
                ApplyStencilRefToRenderers();
            }
        }
#endif

        #endregion

        #region 公开方法

        /// <summary>
        /// 收集子对象中的所有 Renderer 组件
        /// </summary>
        public void CollectRenderers()
        {
            m_Renderers = GetComponentsInChildren<Renderer>();
            m_BoundsDirty = true;
            ApplyStencilRefToRenderers();
        }

        [ContextMenu("Collect Stencil Renderers")]
        public void CollectStencilRenderers()
        {
            if (m_StencilRendererRoot == null)
                return;

            m_StencilRenderers = m_StencilRendererRoot.GetComponentsInChildren<Renderer>(true);
            ApplyStencilRefToRenderers();
        }

        [ContextMenu("Apply Stencil Ref")]
        private void ApplyStencilRefContext()
        {
            ApplyStencilRefToRenderers();
        }

        /// <summary>
        /// 检查组件数据是否有效
        /// </summary>
        public bool IsValid()
        {
            return m_Renderers != null && m_Renderers.Length > 0;
        }

        private void ApplyStencilRefToRenderers()
        {
            var targets = (m_StencilRenderers != null && m_StencilRenderers.Length > 0) ? m_StencilRenderers : m_Renderers;
            if (targets == null) return;

            m_StencilMPB ??= new MaterialPropertyBlock();
            foreach (var r in targets)
            {
                if (r == null) continue;
                r.GetPropertyBlock(m_StencilMPB);
                m_StencilMPB.SetFloat("_StencilRef", m_StencilRef);
                r.SetPropertyBlock(m_StencilMPB);
            }

            // Stencil state can only be modified on the material itself, not via MaterialPropertyBlock.
            // Therefore, we must clone the materials. This is necessary for both play mode and editor preview.
            // The cleanup logic (in OnDisable and OnPlayModeStateChanged) ensures we don't leak materials.
            if (isActiveAndEnabled && Application.isPlaying)
                ApplyStencilRefToSharedMaterials(targets);
        }

        private void ApplyStencilRefToSharedMaterials(Renderer[] targets)
        {
            m_OriginalSharedMaterials ??= new Dictionary<Renderer, Material[]>();
            m_ClonedMaterials ??= new Dictionary<Material, Material>();
            m_OwnedMaterials ??= new List<Material>();

            for (int rIndex = 0; rIndex < targets.Length; rIndex++)
            {
                var r = targets[rIndex];
                if (r == null) continue;

                if (!m_OriginalSharedMaterials.ContainsKey(r))
                    m_OriginalSharedMaterials[r] = r.sharedMaterials;

                var shared = r.sharedMaterials;
                bool changed = false;

                for (int i = 0; i < shared.Length; i++)
                {
                    var src = shared[i];
                    if (src == null) continue;
                    if (!src.HasProperty("_StencilRef")) continue;

                    if (!m_ClonedMaterials.TryGetValue(src, out var inst) || inst == null)
                    {
                        inst = new Material(src);
                        inst.hideFlags = HideFlags.DontSave;
                        m_ClonedMaterials[src] = inst;
                        m_OwnedMaterials.Add(inst);
                    }

                    inst.SetFloat("_StencilRef", m_StencilRef);

                    if (shared[i] != inst)
                    {
                        shared[i] = inst;
                        changed = true;
                    }
                }

                if (changed)
                    r.sharedMaterials = shared;
            }
        }

        private void CleanupStencilMaterials()
        {
            if (m_OriginalSharedMaterials != null)
            {
                foreach (var kv in m_OriginalSharedMaterials)
                {
                    if (kv.Key != null)
                        kv.Key.sharedMaterials = kv.Value;
                }
                m_OriginalSharedMaterials.Clear();
            }

            if (m_OwnedMaterials != null)
            {
                for (int i = 0; i < m_OwnedMaterials.Count; i++)
                {
                    var m = m_OwnedMaterials[i];
                    if (m == null) continue;
                    if (Application.isPlaying)
                        Destroy(m);
                    else
                        DestroyImmediate(m);
                }
                m_OwnedMaterials.Clear();
            }

            m_ClonedMaterials?.Clear();
        }

        #endregion
    }
}
