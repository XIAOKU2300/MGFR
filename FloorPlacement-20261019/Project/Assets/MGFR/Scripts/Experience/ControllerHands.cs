using UnityEngine;
using UnityEngine.XR;
using MGFR.Character;
using MGFR.SmokeTest;

namespace MGFR.Experience
{
    [DefaultExecutionOrder(1100)]
    public sealed class ControllerHands : MonoBehaviour
    {
        public sealed class Hand
        {
            public Transform Palm;
            public Transform[] Fingers;
            public Vector3 Position, Velocity, Offset;
            public bool Active, Grip;
            public Quaternion Rotation=Quaternion.identity;
        }
        public readonly Hand[] Hands={new Hand(),new Hand()};
        public Rigidbody Ball {get;private set;}
        public int BallOwner {get;private set;}=-1;
        public bool DesktopSimulation;
        public bool TestInput;
        SiCharacterLoader loader;
        Camera viewer;
        Transform floor;
        Material handMaterial,ballMaterial;
        float[] simulatedGrip=new float[2];
        Vector3 initialAnchor;

        public void Bind(SiCharacterLoader character)
        {
            loader=character;viewer=Camera.main;initialAnchor=loader.transform.position;
            handMaterial=new Material(Shader.Find("MGFR/Character"));
            handMaterial.SetColor("_Color",new Color(.76f,.53f,.36f));
            ballMaterial=new Material(handMaterial);ballMaterial.SetColor("_Color",new Color(.2f,.6f,1f));
            for(int h=0;h<2;h++)
            {
                var hand=Hands[h];
                hand.Palm=Primitive("Controller hand "+h,PrimitiveType.Sphere,handMaterial);
                hand.Palm.localScale=new Vector3(.07f,.035f,.085f);
                hand.Fingers=new Transform[5];
                for(int f=0;f<5;f++)
                {
                    hand.Fingers[f]=Primitive("Finger "+f,PrimitiveType.Capsule,handMaterial);
                    hand.Fingers[f].SetParent(hand.Palm,false);
                }
                hand.Position=loader.transform.TransformPoint(new Vector3(h==0?.25f:-.25f,1.0f,-.4f));
                hand.Palm.gameObject.SetActive(false);
            }
            var ball=Primitive("Grab and throw ball",PrimitiveType.Sphere,ballMaterial);
            ball.localScale=Vector3.one*.10f;ball.gameObject.AddComponent<SphereCollider>();
            Ball=ball.gameObject.AddComponent<Rigidbody>();Ball.mass=.18f;
            Ball.interpolation=RigidbodyInterpolation.Interpolate;
            Ball.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
            ResetBall();
            floor=new GameObject("Invisible interaction floor").transform;
            var box=floor.gameObject.AddComponent<BoxCollider>();box.size=new Vector3(6,.06f,6);
        }
        static Transform Primitive(string name,PrimitiveType type,Material material)
        {
            // Build only mesh/render components, with no hidden primitive colliders.
            var temp=GameObject.CreatePrimitive(type);
            var mesh=temp.GetComponent<MeshFilter>().sharedMesh;
            temp.SetActive(false);Object.Destroy(temp);
            var go=new GameObject(name);go.AddComponent<MeshFilter>().sharedMesh=mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial=material;return go.transform;
        }
        public void ResetBall()
        {
            BallOwner=-1;Ball.isKinematic=false;
            Ball.position=loader.transform.TransformPoint(new Vector3(0,.9f,-.48f));
            Ball.linearVelocity=Vector3.zero;Ball.angularVelocity=Vector3.zero;
        }
        public void SetSimulatedHand(int h,Vector3 worldPosition,bool grip,bool active=true)
        {
            var hand=Hands[h];hand.Velocity=(worldPosition-hand.Position)/Mathf.Max(Time.deltaTime,.001f);
            hand.Position=worldPosition;hand.Rotation=Quaternion.identity;hand.Active=active;hand.Grip=grip;
        }
        void Update()
        {
            if(Input.GetKeyDown(KeyCode.F2))DesktopSimulation=!DesktopSimulation;
            if(Input.GetKeyDown(KeyCode.F3))ResetBall();
            floor.position=new Vector3(loader.transform.position.x,loader.transform.position.y-.03f,loader.transform.position.z);
            var movement=loader.transform.position-initialAnchor;
            if(movement.sqrMagnitude>.04f){initialAnchor=loader.transform.position;ResetBall();}
            for(int h=0;h<2;h++)
            {
                var hand=Hands[h];
                if(!TestInput)
                {
                    var previous=hand.Position;
                    bool tracked=false;
                    if(!XrDeviceFollower.Suppressed)
                    {
                        var device=InputDevices.GetDeviceAtXRNode(h==0?XRNode.LeftHand:XRNode.RightHand);
                        tracked=device.TryGetFeatureValue(CommonUsages.isTracked,out bool valid)&&valid;
                        if(tracked)
                        {
                            device.TryGetFeatureValue(CommonUsages.devicePosition,out Vector3 position);
                            device.TryGetFeatureValue(CommonUsages.deviceRotation,out Quaternion rotation);
                            device.TryGetFeatureValue(CommonUsages.primary2DAxis,out Vector2 stick);
                            device.TryGetFeatureValue(CommonUsages.grip,out float grip);
                            device.TryGetFeatureValue(CommonUsages.trigger,out float trigger);
                            hand.Offset+=new Vector3(stick.x,0,stick.y)*Time.deltaTime*.25f;
                            hand.Offset=Vector3.ClampMagnitude(hand.Offset,.35f);
                            hand.Position=viewer.transform.parent.TransformPoint(position+hand.Offset);
                            hand.Rotation=viewer.transform.parent.rotation*rotation;
                            hand.Grip=Mathf.Max(grip,trigger)>.55f;
                        }
                    }
                    hand.Active=tracked||DesktopSimulation;
                    if(!tracked&&DesktopSimulation)
                    {
                        if(h==0)
                        {
                            Vector3 d=new Vector3((Input.GetKey(KeyCode.D)?1:0)-(Input.GetKey(KeyCode.A)?1:0),
                                (Input.GetKey(KeyCode.E)?1:0)-(Input.GetKey(KeyCode.Q)?1:0),
                                (Input.GetKey(KeyCode.W)?1:0)-(Input.GetKey(KeyCode.S)?1:0));
                            hand.Position+=loader.transform.rotation*d*Time.deltaTime*.35f;
                        }
                        hand.Grip=simulatedGrip[h]>.5f;
                        hand.Rotation=loader.transform.rotation;
                    }
                    hand.Velocity=(hand.Position-previous)/Mathf.Max(Time.deltaTime,.001f);
                }
                hand.Palm.gameObject.SetActive(hand.Active);
                hand.Palm.SetPositionAndRotation(hand.Position,hand.Rotation);
                for(int f=0;f<5;f++)
                {
                    var finger=hand.Fingers[f];
                    finger.localPosition=new Vector3((f-2)*.19f,hand.Grip?-.25f:0,.48f);
                    finger.localRotation=Quaternion.Euler(hand.Grip?20:80,0,0);
                    finger.localScale=new Vector3(.13f,.35f,.13f);
                }
            }
            UpdateGrab();
        }
        public void UpdateGrab()
        {
            if(BallOwner>=0)
            {
                var hand=Hands[BallOwner];
                if(!hand.Active||!hand.Grip)
                {
                    Ball.isKinematic=false;Ball.linearVelocity=Vector3.ClampMagnitude(hand.Velocity,5f);BallOwner=-1;
                }
                else Ball.position=hand.Position;
            }
            else for(int h=0;h<2;h++)
                if(Hands[h].Active&&Hands[h].Grip&&Vector3.Distance(Hands[h].Position,Ball.position)<.14f)
                {BallOwner=h;Ball.isKinematic=true;Ball.position=Hands[h].Position;break;}
        }
        void OnGUI()
        {
            GUILayout.BeginArea(new Rect(12,Screen.height-155,390,145),GUI.skin.box);
            GUILayout.Label("Hands: controllers + stick offset / grip or trigger to grab");
            GUILayout.Label("F2: desktop hands   F3: reset ball");
            DesktopSimulation=GUILayout.Toggle(DesktopSimulation,"Desktop hand simulation (not hand tracking)");
            if(DesktopSimulation)
            {
                GUILayout.Label("Left: WASD + Q/E height");
                GUILayout.BeginHorizontal();
                simulatedGrip[0]=GUILayout.Toggle(simulatedGrip[0]>.5f,"Left grip")?1:0;
                simulatedGrip[1]=GUILayout.Toggle(simulatedGrip[1]>.5f,"Right grip")?1:0;
                if(GUILayout.Button("Ball to left")){Ball.position=Hands[0].Position;Ball.linearVelocity=Vector3.zero;}
                GUILayout.EndHorizontal();
            }
            GUILayout.EndArea();
        }
    }
}
