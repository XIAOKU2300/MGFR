// Character surface shader for the converted 祀 model.
//
// The Built-in pipeline is in use here (URP is deliberately not installed - see
// unity-client/README.md), and its Standard shader cannot do two things this
// model needs:
//
//   * 目影 (eye shadow) and 发影 (hair shadow) are declared NO_CULL in the PMX.
//     They are flat overlays sitting on top of the face and hair. Rendered
//     single-sided they vanish from half the viewing angles, which reads as
//     "the importer dropped a material".
//   * Blending, depth writing and culling have to be settable per material.
//     Cloth1 is alpha-blended (its texture carries alpha down to 108/255) but
//     must still write depth, or the 29,561 triangles of skirt sort against each
//     other and flicker. 表情 and 发影 must not write depth.
//
// So the three of those are properties rather than hard-coded, and
// SiCharacterLoader picks them per material from the PMX draw flags and the
// texture's own alpha. Everything else is plain Blinn-Phong over the main
// texture, which is what MMD's diffuse pass amounts to.
//
// Deliberately NOT implemented, and reported as such rather than faked:
// sphere maps (all 14 materials declare sphere_mode 0, so there is nothing to
// draw), toon ramp shading, edge/outline rendering, and MMD's per-material
// specular exponent. Edge colour and size are read and exposed but unused.
Shader "MGFR/Character"
{
    Properties
    {
        _MainTex ("Base (RGB) Alpha (A)", 2D) = "white" {}
        _Color ("Diffuse", Color) = (1,1,1,1)
        _SpecTint ("Specular", Color) = (0,0,0,1)
        _Glossiness ("Smoothness", Range(0,1)) = 0.2
        _AmbientColor ("Ambient", Color) = (0.25,0.25,0.25,1)

        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 0
        [Enum(Off,0,On,1)] _ZWrite ("Z Write", Float) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "IgnoreProjector"="True" }

        Pass
        {
            Name "FORWARD"
            Tags { "LightMode"="ForwardBase" }

            Cull [_Cull]
            ZWrite [_ZWrite]
            Blend [_SrcBlend] [_DstBlend]

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fwdbase
            #pragma multi_compile_instancing
            #pragma target 3.5

            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            #include "AutoLight.cginc"

            sampler2D _MainTex;
            float4 _MainTex_ST;
            fixed4 _Color;
            // _SpecTint, not _SpecColor. Lighting.cginc (included below, and pulled
            // in by multi_compile_fwdbase) already declares _SpecColor for the
            // built-in legacy lighting path, so declaring it here is a redefinition
            // and the whole shader fails to compile. A shader that fails to compile
            // still resolves through Shader.Find, so the only symptom is that every
            // surface draws magenta.
            fixed4 _SpecTint;
            float _Glossiness;
            fixed4 _AmbientColor;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 worldNormal : TEXCOORD1;
                float3 worldPos : TEXCOORD2;
                SHADOW_COORDS(3)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert (appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                o.worldNormal = UnityObjectToWorldNormal(v.normal);
                o.worldPos = mul(unity_ObjectToWorld, v.vertex).xyz;
                TRANSFER_SHADOW(o);
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                fixed4 tex = tex2D(_MainTex, i.uv);
                fixed4 c = tex * _Color;

                float3 n = normalize(i.worldNormal);
                float3 l = normalize(_WorldSpaceLightPos0.xyz);

                // abs() rather than saturate(): the two NO_CULL materials are
                // single-sided geometry being drawn from both sides, and without
                // this their back faces go black. Closed geometry is unaffected
                // because its back faces are culled before shading.
                float ndl = abs(dot(n, l));

                UNITY_LIGHT_ATTENUATION(atten, i, i.worldPos);

                fixed3 lit = c.rgb * (ndl * _LightColor0.rgb * atten + _AmbientColor.rgb);

                float3 viewDir = normalize(_WorldSpaceCameraPos - i.worldPos);
                float3 h = normalize(l + viewDir);
                float spec = pow(saturate(abs(dot(n, h))), _Glossiness * 64.0 + 1.0);
                lit += _SpecTint.rgb * spec * ndl * atten;

                return fixed4(lit, c.a);
            }
            ENDCG
        }
    }

    Fallback "Diffuse"
}
