using UnityEngine;

[ExecuteAlways]
public class GlobalRimLightController : MonoBehaviour
{
    [Header("Global Settings")]
    public bool enableRimLight = true;
    
    [Header("Global Shadow Strength")]
    [Range(0f, 1f)] public float selfShadowStrength = 1.0f;
    [Range(0f, 1f)] public float envShadowStrength = 1.0f;

    [Header("Depth Offset Rim (Global)")]
    [Range(0, 0.1f)] public float offsetMul = 0.012f;
    [Range(0, 1f)] public float threshold = 0.09f;
    [Range(0, 1f)] public float smooth = 0.05f;
    public Color rimLightColor = Color.white;
    [Range(0, 5f)] public float rimIntensity = 1.0f;
    [Range(0, 10f)] public float rimLightBrightness = 1.0f;

    [Header("Inner Fresnel Rim (Global)")]
    public Color innerRimColor = Color.white;
    [Range(0.1f, 10f)] public float innerRimPower = 3.0f;
    [Range(0f, 5f)] public float innerRimIntensity = 1.0f;
    [Range(0f, 10f)] public float innerRimBrightness = 1.0f;
    [Range(-1f, 1f)] public float innerRimBias = 0.0f;

    [Header("Rim Light Mask (Pos X & NdotL)")]
    public Vector3 rimLightDirection = new Vector3(1f, 0f, 0f);
    [Range(0.001f, 1f)] public float rimLightSoftness = 0.1f;
    [Range(-1f, 1f)] public float rimLightOffset = 0.0f;

    private void Update()
    {
        Shader.SetGlobalFloat("_Global_EnableRimLight", enableRimLight ? 1f : 0f);
        
        // 角色身上的自阴影强度（在 S_Char_Utils.hlsl 或角色 Shader 中使用）
        Shader.SetGlobalFloat("_Global_ShadowStrength", selfShadowStrength);
        // 投射在地面/环境上的阴影强度（在 PerObjectScreenSpaceShadowReceiver 中使用）
        Shader.SetGlobalFloat("_Global_EnvShadowStrength", envShadowStrength);

        // 传递给 S_Char_Utils.hlsl 中的全局变量
        Shader.SetGlobalFloat("_Global_OffsetMul", offsetMul);
        Shader.SetGlobalFloat("_Global_Threshold", threshold);
        Shader.SetGlobalFloat("_Global_Smooth", smooth);
        Shader.SetGlobalColor("_Global_RimLightColor", rimLightColor);
        Shader.SetGlobalFloat("_Global_RimIntensity", rimIntensity);
        Shader.SetGlobalFloat("_Global_RimLightBrightness", rimLightBrightness);

        Shader.SetGlobalColor("_Global_InnerRimColor", innerRimColor);
        Shader.SetGlobalFloat("_Global_InnerRimPower", innerRimPower);
        Shader.SetGlobalFloat("_Global_InnerRimIntensity", innerRimIntensity);
        Shader.SetGlobalFloat("_Global_InnerRimBrightness", innerRimBrightness);
        Shader.SetGlobalFloat("_Global_InnerRimBias", innerRimBias);

        Shader.SetGlobalVector("_Global_RimLightDirection", rimLightDirection);
        Shader.SetGlobalFloat("_Global_RimLightSoftness", rimLightSoftness);
        Shader.SetGlobalFloat("_Global_RimLightOffset", rimLightOffset);
    }
}