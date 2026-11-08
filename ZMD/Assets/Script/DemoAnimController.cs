using UnityEngine;

public class DemoAnimController : MonoBehaviour
{
    private Animator anim;

    [Header("Auto Fetch Settings")]
    [Tooltip("如果为true，将在运行时自动获取Animator Controller中的动画片段名称并覆盖下方数组（最多取前10个）")]
    public bool autoFetchAnimations = true;

    [Header("Animation State Names for Keys 1-9 and 0")]
    [Tooltip("Index 0 maps to Key 1, Index 1 maps to Key 2... Index 9 maps to Key 0")]
    public string[] animStates = new string[10] {
        "CuteA", "Idle_A", "Rei", "Jump", "Run", 
        "Run_L", "Run_R", "Angpose", "Idle_B", "IdleC"
    };

    [Header("Root Motion Settings")]
    [Tooltip("如果为true，保留Y轴高度变化（如跳跃），丢弃XZ平面的位移。请确保Animator开启了Apply Root Motion。")]
    public bool lockXZRootMotion = true;

    [Header("Auto Play Settings")]
    [Tooltip("开启后自动按顺序循环播放所有动画，每个动画播放指定次数后再播放下一个")]
    public bool autoPlay = false;

    [Header("Auto Play Loop Settings")]
    [Tooltip("每个动画重复播放的次数")]
    public int loopsPerAnim = 3;

    public float crossFadeDuration = 0.1f;

    private int currentAnimIndex = 0;
    private int currentLoopCount = 0;
    private bool isAutoPlaying = false;
    private float animStartTime = 0f;
    private float currentClipLength = 1f;

    void Start()
    {
        anim = GetComponent<Animator>();

        // 自动获取动画片段并填入数组
        if (autoFetchAnimations && anim != null && anim.runtimeAnimatorController != null)
        {
            AnimationClip[] clips = anim.runtimeAnimatorController.animationClips;
            int count = Mathf.Min(clips.Length, 10); // 最多只取前10个，对应0-9按键
            
            for (int i = 0; i < count; i++)
            {
                animStates[i] = clips[i].name;
            }
            
            Debug.Log($"[DemoAnimController] 已自动获取并绑定了 {count} 个动画。");
        }
    }

    void Update()
    {
        if (autoPlay)
        {
            if (!isAutoPlaying)
            {
                isAutoPlaying = true;
                currentAnimIndex = 0;
                currentLoopCount = 0;
                PlayAnim(currentAnimIndex);
            }

            AnimatorStateInfo stateInfo = anim.GetCurrentAnimatorStateInfo(0);
            float clipLen = stateInfo.length;
            if (clipLen > 0.01f)
                currentClipLength = clipLen;

            float elapsed = Time.time - animStartTime;
            float loopDuration = currentClipLength + crossFadeDuration;

            if (elapsed >= loopDuration)
            {
                animStartTime = Time.time;
                currentLoopCount++;
                if (currentLoopCount >= loopsPerAnim)
                {
                    currentAnimIndex = NextValidIndex(currentAnimIndex);
                    currentLoopCount = 0;
                }
                PlayAnim(currentAnimIndex);
            }
        }
        else
        {
            isAutoPlaying = false;

            for (int i = 0; i < 9; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    PlayAnim(i);
                }
            }

            if (Input.GetKeyDown(KeyCode.Alpha0))
            {
                PlayAnim(9);
            }
        }
    }

    // 拦截 Animator 的 Root Motion 默认行为
    void OnAnimatorMove()
    {
        if (anim == null) return;

        if (lockXZRootMotion)
        {
            // 提取动画的旋转
            transform.rotation *= anim.deltaRotation;

            // 提取动画的位移
            Vector3 deltaPosition = anim.deltaPosition;
            // 强制干掉 X 和 Z 轴的位移，只保留 Y 轴（例如跳跃高度）
            deltaPosition.x = 0f;
            deltaPosition.z = 0f;

            // 应用修改后的位移
            transform.position += deltaPosition;
        }
        else
        {
            // 如果不锁定，就执行默认的 Root Motion 行为
            anim.ApplyBuiltinRootMotion();
        }
    }

    private int NextValidIndex(int currentIndex)
    {
        for (int i = 1; i <= animStates.Length; i++)
        {
            int nextIndex = (currentIndex + i) % animStates.Length;
            if (!string.IsNullOrEmpty(animStates[nextIndex]))
                return nextIndex;
        }
        return currentIndex;
    }

    private void PlayAnim(int index)
    {
        if (index >= 0 && index < animStates.Length && !string.IsNullOrEmpty(animStates[index]))
        {
            transform.localPosition = Vector3.zero;
            transform.localRotation = Quaternion.identity;

            anim.CrossFadeInFixedTime(animStates[index], crossFadeDuration, 0, 0f);

            if (autoPlay)
                animStartTime = Time.time;
        }
    }
}