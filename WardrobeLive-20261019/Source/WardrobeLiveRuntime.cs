using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.BareHands;
using MGFR.Skins;
using MGFR.Skins.ClothPhysics;
using UnityEngine;

namespace MGFR.Wardrobe
{
    [DefaultExecutionOrder(1350)]
    public sealed class WardrobeLiveRuntime : MonoBehaviour, IWardrobeDeformationOwner
    {
        public static WardrobeLiveRuntime Instance {get;private set;}
        public bool IsReady=>adapter!=null;
        public bool Enabled {get;private set;}=true;
        public bool Manual;
        public int DetachCount {get;private set;}
        public int EquipCount {get;private set;}
        public int LossCancels {get;private set;}
        public string Status {get;private set;}="等待泳装";
        public WardrobeAdapter Adapter=>adapter;
        public BareHandInteraction Hands=>hands;
        public SwimsuitClothRuntime Cloth=>cloth;
        SiSkinSwitcher skins;BareHandInteraction hands;SwimsuitClothRuntime cloth;
        WardrobeAdapter adapter;bool boundStyle;Font font;GameObject marker;
        readonly HandPinchState[] pinches={new HandPinchState(),new HandPinchState()};
        sealed class Interaction
        {
            public bool blocked=true;public string pending,held;public int anchor;
            public Vector3 startLocal,last;public float elapsed;
            public Quaternion rotationOffset;
        }
        sealed class Piece
        {public GameObject go;public Vector3 grip;public int anchor;public int owner=-1;}
        readonly Interaction[] state={new Interaction(),new Interaction()};
        readonly Dictionary<string,Piece> pieces=new Dictionary<string,Piece>();
        static bool Has(string flag)=>Array.IndexOf(Environment.GetCommandLineArgs(),flag)>=0;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {if(Has("-mgfr-wardrobe"))new GameObject("Hand wardrobe runtime").AddComponent<WardrobeLiveRuntime>();}
        IEnumerator Start()
        {
            Instance=this;
            while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||
                (hands=FindAnyObjectByType<BareHandInteraction>())==null||!hands.IsReady||
                (cloth=FindAnyObjectByType<SwimsuitClothRuntime>())==null)yield return null;
            skins.BeforeAppearanceChange+=BeforeSkinChange;
            font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",16);
        }
        void BeforeSkinChange(){EndSession();}
        void Update()
        {
            if(!Input.GetKeyDown(KeyCode.F12))return;
            if(Input.GetKey(KeyCode.LeftShift)||Input.GetKey(KeyCode.RightShift)){ResetAll();return;}
            Enabled=!Enabled;CancelHands();Status=Enabled?"穿脱已开启":"穿脱已关闭，布料捏拉保留";
        }
        void LateUpdate(){if(!Manual)Step(Time.deltaTime);}
        public bool OwnsHand(int h)=>adapter!=null&&(state[h].pending!=null||state[h].held!=null);
        public bool IsEquipped(string id)=>adapter!=null&&adapter.IsEquipped(id);
        public string Held(int h)=>state[h].held;
        public string Pending(int h)=>state[h].pending;
        public Vector3 Socket(string id,int anchor=0)
        {
            var part=adapter.GetPart(id);
            if(part.materialSlot==10&&cloth.TryWardrobeVertex(part.anchors[anchor].vertex,out var p))return p;
            return adapter.AnchorWorld(id,anchor);
        }
        public Vector3 DroppedGrip(string id)=>pieces[id].go.transform.TransformPoint(pieces[id].grip);
        public void Step(float dt)
        {
            if(skins==null||!skins.IsReady||hands==null||!hands.IsReady||cloth==null)return;
            if(skins.CurrentId!="swimsuit") {if(adapter!=null)EndSession();return;}
            if(!cloth.IsReady)return;
            if(adapter!=null&&boundStyle!=skins.Style.Active)EndSession();
            if(adapter==null)
            {
                adapter=new WardrobeAdapter(skins.Loader.Renderer,Path.Combine(Application.streamingAssetsPath,"wardrobe/barefoot_v4"),cloth.FullRenderMesh);
                adapter.SimulatedClothActive=true;adapter.ClothOwner=this;
                boundStyle=skins.Style.Active;cloth.SetWardrobeMesh(adapter.VisibleMesh);
                Status="张手后，捏住扣点向外拉脱";
                Debug.Log("[Wardrobe] Ready: 8 parts, shared hand ownership and XPBD part handoff; F12 toggle, Shift+F12 restore.");
            }
            dt=Mathf.Clamp(dt,0,.05f);
            for(int h=0;h<2;h++)StepHand(h,dt);
            UpdateMarker();
        }
        void StepHand(int h,float dt)
        {
            var s=state[h];var f=hands.Source.Frames[h];
            bool tracked=Enabled&&hands.PreferBareHands&&hands.Physics.Simulate&&f.Tracked&&f.CanStartPinch&&Time.unscaledTime-f.Timestamp<=.12f;
            if(!tracked)
            {
                if(OwnsHand(h)){LossCancels++;Cancel(h);}
                pinches[h].Reset();s.blocked=true;s.last=Vector3.zero;return;
            }
            Vector3 point=f.PinchPoint;
            if(s.last!=Vector3.zero&&Vector3.Distance(s.last,point)>.18f)
            {Cancel(h);pinches[h].Reset();s.blocked=true;s.last=point;return;}
            s.last=point;
            bool closed=pinches[h].Update(f,dt);
            if(!closed)
            {
                bool open=Vector3.Distance(f.Joints[5].position,f.Joints[10].position)>
                    Mathf.Clamp(f.Radius[5]+f.Radius[10],.009f,.032f)+.020f*f.Scale;
                if(!open)return;
                if(s.held!=null)ReleaseHeld(h,true);
                if(s.pending!=null)CancelPending(h);
                s.blocked=false;return;
            }
            if(s.blocked)return;
            if(s.held!=null)
            {
                var p=pieces[s.held];
                p.go.transform.rotation=f.Joints[1].rotation*s.rotationOffset;
                p.go.transform.position+=point-p.go.transform.TransformPoint(p.grip);
                hands.GrabStatus[h]="手持："+adapter.GetPart(s.held).label;
                return;
            }
            if(s.pending!=null)
            {
                s.elapsed+=dt;
                var part=adapter.GetPart(s.pending);var root=skins.Loader.transform;
                Vector3 delta=root.InverseTransformPoint(point)-s.startLocal;
                Vector3 direction=new Vector3(part.pullDirectionLocal[0],part.pullDirectionLocal[1],part.pullDirectionLocal[2]);
                if(part.materialSlot==10&&cloth.Solver.Grips[h].particle>=0)cloth.Solver.MoveGrip(h,point);
                if(Vector3.Dot(delta,direction)>=part.pullDistanceMetres&&s.elapsed>=.12f)
                {
                    string id=s.pending;
                    if(adapter.TryDetach(id,out var go,out var reason))
                    {
                        var vertices=go.GetComponent<MeshFilter>().sharedMesh.vertices;
                        pieces.Add(id,new Piece{go=go,grip=vertices[part.anchors[s.anchor].vertex],anchor=s.anchor});
                        s.pending=null;cloth.Solver.Release(h);cloth.SetWardrobeMesh(adapter.VisibleMesh);
                        Hold(h,id);DetachCount++;Status="已脱下："+part.label+"；对准提示点松手穿回";
                    }
                    else {Status=reason;CancelPending(h);s.blocked=true;}
                }
                else if(s.elapsed>4||delta.magnitude>.45f){CancelPending(h);s.blocked=true;}
                return;
            }
            // A held pinch never acquires again after a completed action.
            if(!pinches[h].CanAcquire)return;
            string pick=null;int pickAnchor=0;float best=.05f*.05f;
            foreach(var pair in pieces)
            {
                if(pair.Value.owner>=0)continue;
                float distance=(DroppedGrip(pair.Key)-point).sqrMagnitude;
                if(distance<best){best=distance;pick=pair.Key;}
            }
            if(pick!=null){Hold(h,pick);return;}
            if(hands.GrabbedBody[h]>=0)return;
            foreach(var part in adapter.Profile.parts)
            {
                if(!adapter.IsEquipped(part.id)||part.id==state[1-h].pending)continue;
                for(int i=0;i<part.anchors.Length;i++)
                {
                    float distance=(Socket(part.id,i)-point).sqrMagnitude;
                    float reach=part.gripRadiusMetres*Mathf.Abs(skins.Loader.transform.lossyScale.x);
                    if(distance<best&&distance<reach*reach){best=distance;pick=part.id;pickAnchor=i;}
                }
            }
            if(pick==null)return;
            s.pending=pick;s.anchor=pickAnchor;s.elapsed=0;s.startLocal=skins.Loader.transform.InverseTransformPoint(point);
            hands.CancelForWardrobe(h);
            var selected=adapter.GetPart(pick);
            if(selected.materialSlot==10)cloth.Solver.Grab(h,point,.045f);
            Status="捏住："+selected.label+"，沿衣物方向拉开";
        }
        void Hold(int h,string id)
        {
            var s=state[h];var p=pieces[id];p.owner=h;s.held=id;s.pending=null;s.anchor=p.anchor;
            s.rotationOffset=Quaternion.Inverse(hands.Source.Frames[h].Joints[1].rotation)*p.go.transform.rotation;
            hands.CancelForWardrobe(h);
        }
        void ReleaseHeld(int h,bool mayEquip)
        {
            var s=state[h];string id=s.held;if(id==null)return;
            var p=pieces[id];var part=adapter.GetPart(id);
            float scale=Mathf.Abs(skins.Loader.transform.lossyScale.x);
            bool near=Vector3.Distance(p.go.transform.TransformPoint(p.grip),Socket(id,p.anchor))<=part.snapRadiusMetres*scale;
            bool facing=Quaternion.Angle(p.go.transform.rotation,skins.Loader.Renderer.transform.rotation)<=part.snapAngleDegrees;
            if(mayEquip&&near&&facing&&adapter.TryEquip(id,out _))
            {
                pieces.Remove(id);cloth.SetWardrobeMesh(adapter.VisibleMesh);EquipCount++;Status="已穿回："+part.label;
            }
            else
            {
                p.owner=-1;p.go.transform.rotation=skins.Loader.Renderer.transform.rotation;
                int index=Array.FindIndex(adapter.Profile.parts,x=>x.id==id);
                Vector3 rack=skins.Loader.transform.TransformPoint(new Vector3(.60f+(index%2)*.24f,.48f+(index/2)*.18f,-.18f));
                p.go.transform.position+=rack-p.go.transform.TransformPoint(p.grip);
                Status="已放到身旁置物位："+part.label;
            }
            s.held=null;s.blocked=true;
        }
        void CancelPending(int h){state[h].pending=null;state[h].elapsed=0;if(cloth?.Solver!=null)cloth.Solver.Release(h);}
        void Cancel(int h){if(state[h].held!=null)ReleaseHeld(h,false);CancelPending(h);state[h].blocked=true;}
        void CancelHands(){for(int h=0;h<2;h++){Cancel(h);pinches[h].Reset();state[h].blocked=true;}}
        public void ResetAll(){EndSession();Status="已复原全部部件";}
        void EndSession()
        {
            if(adapter==null)return;
            CancelHands();var mesh=adapter.VisibleMesh;
            cloth.ReleaseWardrobeMesh(mesh);adapter.Dispose();adapter=null;pieces.Clear();
            if(marker!=null)marker.SetActive(false);
        }
        public bool TrySuspendPart(string id,out Vector3[] currentVerticesInModelSpace)=>cloth.SuspendWardrobePart(id,out currentVerticesInModelSpace);
        public void ResumePart(string id)=>cloth.ResumeWardrobePart(id);
        void UpdateMarker()
        {
            int h=state[0].held!=null?0:state[1].held!=null?1:-1;
            if(h<0){if(marker!=null)marker.SetActive(false);return;}
            if(marker==null)
            {
                marker=GameObject.CreatePrimitive(PrimitiveType.Sphere);marker.name="穿回位置提示";
                Destroy(marker.GetComponent<Collider>());
                var mat=new Material(skins.Loader.Materials[7]);mat.SetTexture("_MainTex",Texture2D.whiteTexture);mat.SetColor("_Color",new Color(.1f,.8f,1f));
                marker.GetComponent<Renderer>().sharedMaterial=mat;
            }
            marker.SetActive(true);marker.transform.position=Socket(state[h].held,state[h].anchor);
            marker.transform.localScale=Vector3.one*.022f*Mathf.Abs(skins.Loader.transform.lossyScale.x);
        }
        void OnGUI()
        {
            if(font==null)return;var old=GUI.skin.font;GUI.skin.font=font;
            GUILayout.BeginArea(new Rect(Screen.width-440,20,420,112),GUI.skin.box);
            GUILayout.Label("泳装穿脱："+(Enabled?"开启":"关闭")+"  F12 切换 / Shift+F12 复原");
            GUILayout.Label("张手 → 扣点捏合 → 拉脱；对准蓝点松手穿回");GUILayout.Label(Status);
            GUILayout.EndArea();GUI.skin.font=old;
        }
        void OnDestroy()
        {
            if(skins!=null)skins.BeforeAppearanceChange-=BeforeSkinChange;
            EndSession();if(Instance==this)Instance=null;
            if(marker!=null){Destroy(marker.GetComponent<Renderer>().sharedMaterial);Destroy(marker);}
            if(font!=null)Destroy(font);
        }
    }
}
