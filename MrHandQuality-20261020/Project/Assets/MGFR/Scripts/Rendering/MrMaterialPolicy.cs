using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace MGFR.Rendering
{
    // Profiles refer to this model's named material slots, not an arbitrary alpha atlas.
    public static class MrMaterialPolicy
    {
        sealed class State
        {
            public Material material; public int queue, slot;
            public float src, dst, depth, clip; public bool hasClip;
            public string kind; public float threshold;
        }
        static readonly Dictionary<Material, State> states = new Dictionary<Material, State>();
        static readonly Dictionary<Texture2D, Vector3> distributions = new Dictionary<Texture2D, Vector3>();
        public static bool Active { get; private set; }
        public static float ClipThreshold = .18f;
        public static int MaterialCount => states.Count;
        static float Get(Material m,string p,float fallback) => m.HasProperty(p)?m.GetFloat(p):fallback;
        static void Set(Material m,string p,float v) { if(m.HasProperty(p))m.SetFloat(p,v); }
        static Texture TextureOf(Material m)=>m.HasProperty("_BaseColor")?m.GetTexture("_BaseColor"):m.mainTexture;
        static State DesktopState(Material source)
        {
            if(states.TryGetValue(source,out var exact))return exact;
            if(source.name.Length>=2&&int.TryParse(source.name.Substring(0,2),out int slot))
                foreach(var item in states.Values)if(item.material!=null&&item.slot==slot&&TextureOf(item.material)==TextureOf(source))return item;
            return null;
        }
        public static void InheritDesktop(Material destination, Material source)
        {
            var s=DesktopState(source);if(s==null)return;
            destination.renderQueue=s.queue; Set(destination,"_SrcBlend",s.src);
            Set(destination,"_DstBlend",s.dst); Set(destination,"_ZWrite",s.depth);
            if(s.hasClip)Set(destination,"_AlphaClip",s.clip);
            Set(destination,"_MrCoverage",0);
        }
        public static void Register(Material m,int slot)
        {
            if(m==null || states.ContainsKey(m))return;
            if(Get(m,"_MrCoverage",0)>.5f)InheritDesktop(m,m);
            var texture=(m.HasProperty("_BaseColor")?m.GetTexture("_BaseColor"):m.mainTexture) as Texture2D;
            Vector3 alpha=new Vector3(0,0,1);
            if(texture!=null && !distributions.TryGetValue(texture,out alpha))
            {
                alpha=new Vector3(0,0,1);
                if(texture.isReadable)
                {
                    var pixels=texture.GetPixels32(); int zero=0,mid=0,opaque=0;
                    foreach(var p in pixels) { if(p.a<8)zero++;else if(p.a<250)mid++;else opaque++; }
                    if(pixels.Length>0)alpha=new Vector3(zero,mid,opaque)/pixels.Length;
                }
                distributions[texture]=alpha;
            }
            string kind=slot==4||slot==10||slot==11||slot==13?"authored-translucent":
                slot==0||slot==7?"opaque-body":slot==1||slot==2||slot==3||slot==5||slot==6||slot==12?"cutout":
                slot==8||slot==9?(alpha.x>.001f?"cutout":"opaque-clothing"):"unknown-preserved";
            var s=new State{material=m,slot=slot,queue=m.renderQueue,src=Get(m,"_SrcBlend",1),dst=Get(m,"_DstBlend",0),
                depth=Get(m,"_ZWrite",1),clip=Get(m,"_AlphaClip",0),hasClip=m.HasProperty("_AlphaClip"),kind=kind,
                threshold=kind=="cutout"?ClipThreshold:0};
            states.Add(m,s);
            Debug.Log($"[MR material] name={m.name} slot={slot} policy={kind} alphaZero={alpha.x:F5} alphaMid={alpha.y:F5} alphaOpaque={alpha.z:F5} cutoff={s.threshold:F3}");
            Apply(s);
        }
        static void Apply(State s)
        {
            var m=s.material; if(m==null)return;
            bool cover=Active && (s.kind=="cutout"||s.kind.StartsWith("opaque")) && m.HasProperty("_MrCoverage");
            Set(m,"_MrCoverage",cover?1:0); Set(m,"_MrCutoff",s.threshold);
            Set(m,"_SrcBlend",cover?(float)BlendMode.One:s.src);
            Set(m,"_DstBlend",cover?(float)BlendMode.Zero:s.dst);
            Set(m,"_ZWrite",cover?1:s.depth);
            if(s.hasClip)Set(m,"_AlphaClip",cover?s.threshold:s.clip);
            m.renderQueue=cover?(s.kind=="cutout"?(int)RenderQueue.AlphaTest:(int)RenderQueue.Geometry):s.queue;
        }
        public static void SetActive(bool value)
        {
            if(Active==value)return;Active=value; foreach(var s in states.Values)Apply(s);
        }
        public static void RegisterArray(Material[] materials)
        { for(int i=0;i<materials.Length;i++)Register(materials[i],i); }
    }
}
