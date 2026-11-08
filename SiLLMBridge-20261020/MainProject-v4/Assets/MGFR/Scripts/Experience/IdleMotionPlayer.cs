using System;
using System.IO;
using UnityEngine;
using MGFR.Character;
using MGFR.Attention;
using MGFR.Dialogue;

namespace MGFR.Experience
{
    [DefaultExecutionOrder(800)]
    public sealed class IdleMotionPlayer : MonoBehaviour
    {
        Transform[] bones;
        Vector3[] rest;
        Vector3[,] positions;
        Quaternion[,] rotations;
        int[] indices;
        int frames;
        float fps;
        FaceAttentionController attention;
        public float Duration => (frames-1)/fps;
        public int BoundBones => indices.Length;
        public float Phase { get; private set; }
        public bool Playing = true;
        public float ManualTime = -1;
        float clock;
        public bool NaturalIdle = System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-mgfr-legacy-idle") < 0;
        public NaturalIdlePose Natural {get;} = new NaturalIdlePose();
        public float MotionSeconds {get;private set;}
        public float LastNaturalMilliseconds {get;private set;}
        float naturalBlend=1;
        public NaturalLowerBody Lower {get;}=new NaturalLowerBody();
        public LowerBodyPose LowerPose {get;private set;}
        public float LowerStrength {get;private set;}
        float legClock,legRate=1;
        MGFR.Skins.SiSkinSwitcher wardrobe;
        void Update(){if(Input.GetKeyDown(KeyCode.F6))NaturalIdle=!NaturalIdle;}
        DialogueClient client;readonly SpeechMotionState speech=new SpeechMotionState();
        DialogueAudioOutput audio;
        Quaternion[] speechRest,speechBasis,naturalRest;
        Quaternion[] lastPose;
        public SpokenGestureState Gestures {get;}=new SpokenGestureState();
        public float SpeakingBlend=>speech.Weight;
        public bool SpeechActive=>speech.Active;

        public void Bind(SiCharacterLoader loader, FaceAttentionController face)
        {
            attention=face; bones=loader.Renderer.bones;BindClient();
            wardrobe=FindAnyObjectByType<MGFR.Skins.SiSkinSwitcher>();
            rest=new Vector3[bones.Length];
            for(int i=0;i<bones.Length;i++)rest[i]=bones[i].localPosition;
            using(var reader=new BinaryReader(File.OpenRead(Path.Combine(Application.streamingAssetsPath,"motion/idle.bin"))))
            {
                if(reader.ReadUInt32()!=0x454C4449)throw new InvalidDataException("Expected baked IDLE motion");
                int count=reader.ReadInt32();frames=reader.ReadInt32();fps=reader.ReadSingle();
                indices=new int[count];
                for(int i=0;i<count;i++)indices[i]=reader.ReadInt32();
                positions=new Vector3[frames,count];rotations=new Quaternion[frames,count];
                for(int f=0;f<frames;f++)for(int i=0;i<count;i++)
                {
                    positions[f,i]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                    rotations[f,i]=new Quaternion(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                }
            }
            CalibrateSpeakingRest(loader.transform);CalibrateNaturalRest(loader.transform);
            lastPose=new Quaternion[bones.Length];for(int i=0;i<bones.Length;i++)lastPose[i]=bones[i].localRotation;
            Debug.Log($"[MGFR idle] {BoundBones} baked bones, {Duration:F3}s loop; live mouth/blink retained");
        }
        public void RebindSkinRestPose(SiCharacterLoader loader)
        {
            // Preserve playback clock, speech state and the live pose. Calibrate
            // speaking axes in the target rest pose rather than an animated pose.
            var savedPositions = new Vector3[bones.Length];
            var savedRotations = new Quaternion[bones.Length];
            for (int i = 0; i < bones.Length; i++)
            {
                savedPositions[i] = bones[i].localPosition;
                savedRotations[i] = bones[i].localRotation;
                var p = loader.Data.bones[i].localScaled;
                rest[i] = new Vector3(p[0], p[1], p[2]);
                bones[i].localPosition = rest[i]; bones[i].localRotation = Quaternion.identity;
            }
            CalibrateSpeakingRest(loader.transform);CalibrateNaturalRest(loader.transform);
            for (int i = 0; i < bones.Length; i++)
            {
                bones[i].localPosition = savedPositions[i];
                bones[i].localRotation = savedRotations[i];
                lastPose[i] = savedRotations[i];
            }
        }
        void BindClient()
        {
            if(client!=null)return;
            client=FindAnyObjectByType<DialogueClient>();
            if(client==null)return;
            audio=client.GetComponent<DialogueAudioOutput>();client.SentenceQueued+=Gestures.Queue;
        }
        static bool ArmChain(int bone)=>(bone>=29&&bone<=38)||(bone>=55&&bone<=64);
        void CalibrateSpeakingRest(Transform root)
        {
            speechRest=new Quaternion[bones.Length];speechBasis=new Quaternion[bones.Length];
            var original=new Quaternion[bones.Length];
            for(int i=0;i<bones.Length;i++){original[i]=bones[i].localRotation;speechRest[i]=original[i];}
            // The baked idle has an asymmetric folded arm. Talking needs its own
            // relaxed rest, calibrated from this model's actual repaired skeleton.
            foreach(int arm in new[]{32,58})
            {
                int elbow=arm==32?35:61;
                Vector3 current=bones[elbow].position-bones[arm].position;
                float side=Mathf.Sign(root.InverseTransformDirection(current).x);
                Vector3 down=root.TransformDirection(new Vector3(side*.45f,-1,-.08f).normalized);
                bones[arm].rotation=Quaternion.FromToRotation(current,down)*bones[arm].rotation;
            }
            for(int i=0;i<bones.Length;i++)
            {speechRest[i]=bones[i].localRotation;speechBasis[i]=Quaternion.Inverse(root.rotation)*bones[i].rotation;}
            for(int i=0;i<bones.Length;i++)bones[i].localRotation=original[i];
        }
        void CalibrateNaturalRest(Transform root)
        {
            var saved=new Quaternion[bones.Length];naturalRest=new Quaternion[bones.Length];
            for(int i=0;i<bones.Length;i++)saved[i]=bones[i].localRotation;
            foreach(int arm in new[]{32,58})
            {
                int elbow=arm==32?35:61,wrist=arm==32?38:64;float side=arm==32?1:-1;
                var down=root.TransformDirection(new Vector3(side*.12f,-1,-.06f).normalized);
                bones[arm].rotation=Quaternion.FromToRotation(bones[elbow].position-bones[arm].position,down)*bones[arm].rotation;
                var forearm=root.TransformDirection(new Vector3(side*.045f,-1,-.20f).normalized);
                bones[elbow].rotation=Quaternion.FromToRotation(bones[wrist].position-bones[elbow].position,forearm)*bones[elbow].rotation;
            }
            for(int i=0;i<bones.Length;i++)naturalRest[i]=bones[i].localRotation;
            for(int i=0;i<bones.Length;i++)bones[i].localRotation=saved[i];
        }
        void LateUpdate()
        {
            var wardrobeLive=MGFR.Wardrobe.WardrobeLiveRuntime.Instance;
            bool handling=false;
            if(wardrobeLive!=null&&wardrobeLive.IsReady)for(int h=0;h<2;h++)
                handling|=wardrobeLive.Pending(h)!=null||wardrobeLive.Held(h)!=null;
            legRate=Mathf.MoveTowards(legRate,handling?0:1,Time.deltaTime/.25f);
            if(Playing){clock+=Time.deltaTime;legClock+=Time.deltaTime*legRate;}
            BindClient();
            if(client!=null)speech.Tick(client.IsSpeaking,audio!=null&&audio.PlaybackPending,client.CurrentRound,Time.unscaledTimeAsDouble,Time.unscaledDeltaTime);
            if(audio!=null)Gestures.Tick(client.CurrentRound,audio.PlaybackCursor,audio.PlaybackRate,
                audio.PlaybackPending,client.IsSpeaking,Time.unscaledTimeAsDouble,Time.unscaledDeltaTime,attention,client.LastAsrText);
            Apply(ManualTime>=0?ManualTime:clock);
        }
        internal void ReviewPlayback(bool audible,int round,double now,float delta)
        {speech.Tick(audible,audible,round,now,delta);}
        public void Apply(float seconds,float frameDelta=-1)
        {
            MGFR.Wardrobe.ShoeFootPose.Instance?.UndoLift();
            float poseDelta=Mathf.Min(frameDelta>=0?frameDelta:Time.unscaledDeltaTime,.033f);
            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            MotionSeconds=seconds;
            naturalBlend=Mathf.MoveTowards(naturalBlend,NaturalIdle?1:0,poseDelta/.9f);
            LowerStrength=naturalBlend*(1-.35f*speech.Weight);
            LowerPose=Lower.Sample(frameDelta>=0||ManualTime>=0?seconds:legClock,LowerStrength);
            Phase=Mathf.Repeat(seconds,Duration)*fps;
            int a=(int)Phase,b=Mathf.Min(a+1,frames-1);float t=Phase-a;
            for(int i=0;i<indices.Length;i++)
            {
                int index=indices[i];
                // Attention is the final head/eye writer. Pass it a small idle nod.
                if(index==16||index==17||index==18||index==19||index==20)continue;
                var position=Vector3.Lerp(positions[a,i],positions[b,i],t);
                var rotation=Quaternion.Slerp(rotations[a,i],rotations[b,i],t);
                int restFrame=Mathf.Min((int)(.9f*fps),frames-1);
                var calmPosition=positions[restFrame,i];
                // Rest IK targets remove the source costume's permanent lifted
                // foot. Authored foot swings and shoe height are layered later.
                if(index==0||index==1||index==3||(index>=6&&index<=11))calmPosition=Vector3.zero;
                var calmRotation=ArmChain(index)?naturalRest[index]:rotations[restFrame,i];
                if((index>=43&&index<=54)||(index>=69&&index<=80))
                {
                    int digit=(index>=69?index-69:index-43),joint=digit%3,finger=digit/3;
                    float curl=joint==0?14+finger*2:joint==1?10+finger:5+finger;
                    calmRotation=Quaternion.Euler(0,0,(index>=69?1:-1)*curl);
                }
                if((index>=40&&index<=42)||(index>=66&&index<=68))
                    calmRotation=Quaternion.Slerp(Quaternion.identity,rotations[restFrame,i],.3f);
                if(index==0||index==1||index==3||index==5||index==12||(index>=6&&index<=11))calmRotation=Quaternion.identity;
                position=Vector3.Lerp(position,calmPosition,naturalBlend);
                rotation=Quaternion.Slerp(rotation,calmRotation,naturalBlend);
                if(SpeechMotionState.AffectsBone(index)||ArmChain(index))
                {
                    int neutral=Mathf.Min((int)(.9f*fps),frames-1);
                    position=Vector3.Lerp(position,positions[neutral,i],speech.Weight);
                    var neutralRotation=ArmChain(index)?speechRest[index]:rotations[neutral,i];
                    var talking=neutralRotation*SpeechMotionState.BoneOffset(index,clock)*Gestures.Offset(index,speechBasis[index]);
                    rotation=Quaternion.Slerp(rotation,talking,speech.Weight);
                }
                if(naturalBlend>0)
                {
                    float weight=naturalBlend*(ArmChain(index)?1-speech.Weight:1-.35f*speech.Weight);
                    position+=Natural.Translation(index,seconds)*weight;
                    rotation*=Quaternion.Euler(Natural.Angles(index,seconds)*weight);
                }
                if(index==5)position+=LowerPose.Hips;
                if(index==12)rotation*=Quaternion.Euler(LowerPose.Pelvis);
                // Sleeves must have time to follow the arm during both idle and
                // speech transitions. A display hitch cannot jump the rig ahead.
                bones[index].localPosition=rest[index]+position;bones[index].localRotation=rotation;
                if(index==14||index==15)
                {
                    float expansion=(Natural.Breath(seconds,index==14?.06f:.13f)-.44f)*naturalBlend*(1-.25f*speech.Weight);
                    // Ribcage expansion, not a whole-character vertical bob.
                    Vector3 amount=index==14?new Vector3(.0025f,.0008f,.004f):new Vector3(.004f,.0012f,.006f);
                    bones[index].localScale=Vector3.one+amount*expansion;
                }
            }
            // The source clip has no spine-14 track. Drive it explicitly from
            // the current skin's rest pose, otherwise the middle breath layer is
            // silently absent. Assign absolute deltas to avoid accumulation.
            float midWeight=naturalBlend*(1-.35f*speech.Weight);
            bones[14].localPosition=rest[14]+Natural.Translation(14,seconds)*midWeight;
            bones[14].localRotation=Quaternion.Euler(Natural.Angles(14,seconds)*midWeight);
            bones[14].localScale=Vector3.one+new Vector3(.0025f,.0008f,.004f)*
                ((Natural.Breath(seconds,.06f)-.44f)*midWeight);
            // The source idle comes from another costume. Keep the elbows just
            // outside this model's long sleeve/hip silhouette before rate limiting.
            for(int hand=0;hand<2;hand++)
            {
                int arm=hand==0?32:58;
                int elbow=arm==32?35:61;float side=arm==32?1:-1;
                Vector3 target=transform.InverseTransformPoint(bones[elbow].position);
                float clearance=.33f*(1-naturalBlend);
                if(naturalBlend<.999f&&side*target.x<clearance)
                {
                    target.x=side*clearance;
                    var direction=bones[elbow].position-bones[arm].position;
                    var clear=transform.TransformPoint(target)-bones[arm].position;
                    bones[arm].rotation=Quaternion.FromToRotation(direction,clear)*bones[arm].rotation;
                }
            }
            foreach(int index in indices)if(ArmChain(index))
            {
                var rotation=Quaternion.RotateTowards(lastPose[index],bones[index].localRotation,(index==35||index==61?150:115)*poseDelta);
                bones[index].localRotation=lastPose[index]=rotation;
            }
            for(int i=0;i<indices.Length;i++)if(indices[i]==17)
            {
                var e=Quaternion.Slerp(rotations[a,i],rotations[b,i],t).eulerAngles;
                e=new Vector3(Mathf.DeltaAngle(0,e.x),Mathf.DeltaAngle(0,e.y),Mathf.DeltaAngle(0,e.z))*.35f;
                e=Vector3.Lerp(e,Natural.Head(seconds),naturalBlend);
                attention.SubmitHeadGesture(Vector3.Lerp(e,SpeechMotionState.HeadOffset(clock)+Gestures.Head,speech.Weight),Time.unscaledTime);
            }
            LastNaturalMilliseconds=(float)((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000d/System.Diagnostics.Stopwatch.Frequency);
        }
        void OnDestroy(){if(client!=null)client.SentenceQueued-=Gestures.Queue;}
    }
}
