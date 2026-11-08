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
        DialogueClient client;readonly SpeechMotionState speech=new SpeechMotionState();
        DialogueAudioOutput audio;
        Quaternion[] speechRest,speechBasis;
        Quaternion[] lastPose;
        public SpokenGestureState Gestures {get;}=new SpokenGestureState();
        public float SpeakingBlend=>speech.Weight;
        public bool SpeechActive=>speech.Active;

        public void Bind(SiCharacterLoader loader, FaceAttentionController face)
        {
            attention=face; bones=loader.Renderer.bones;BindClient();
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
            CalibrateSpeakingRest(loader.transform);
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
            CalibrateSpeakingRest(loader.transform);
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
        void LateUpdate()
        {
            if(Playing)clock+=Time.deltaTime;
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
            float poseDelta=Mathf.Min(frameDelta>=0?frameDelta:Time.unscaledDeltaTime,.033f);
            Phase=Mathf.Repeat(seconds,Duration)*fps;
            int a=(int)Phase,b=Mathf.Min(a+1,frames-1);float t=Phase-a;
            for(int i=0;i<indices.Length;i++)
            {
                int index=indices[i];
                // Attention is the final head/eye writer. Pass it a small idle nod.
                if(index==16||index==17||index==18||index==19||index==20)continue;
                var position=Vector3.Lerp(positions[a,i],positions[b,i],t);
                var rotation=Quaternion.Slerp(rotations[a,i],rotations[b,i],t);
                if(SpeechMotionState.AffectsBone(index)||ArmChain(index))
                {
                    int neutral=Mathf.Min((int)(.9f*fps),frames-1);
                    position=Vector3.Lerp(position,positions[neutral,i],speech.Weight);
                    var neutralRotation=ArmChain(index)?speechRest[index]:rotations[neutral,i];
                    var talking=neutralRotation*SpeechMotionState.BoneOffset(index,clock)*Gestures.Offset(index,speechBasis[index]);
                    rotation=Quaternion.Slerp(rotation,talking,speech.Weight);
                }
                // Sleeves must have time to follow the arm during both idle and
                // speech transitions. A display hitch cannot jump the rig ahead.
                bones[index].localPosition=rest[index]+position;bones[index].localRotation=rotation;
            }
            // The source idle comes from another costume. Keep the elbows just
            // outside this model's long sleeve/hip silhouette before rate limiting.
            for(int hand=0;hand<2;hand++)
            {
                int arm=hand==0?32:58;
                int elbow=arm==32?35:61;float side=arm==32?1:-1;
                Vector3 target=transform.InverseTransformPoint(bones[elbow].position);
                if(side*target.x<.33f)
                {
                    target.x=side*.33f;
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
                attention.SubmitHeadGesture(Vector3.Lerp(e,SpeechMotionState.HeadOffset(clock)+Gestures.Head,speech.Weight),Time.unscaledTime);
            }
        }
        void OnDestroy(){if(client!=null)client.SentenceQueued-=Gestures.Queue;}
    }
}
