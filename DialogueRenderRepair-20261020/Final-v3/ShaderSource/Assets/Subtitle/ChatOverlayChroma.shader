Shader "MGFR/ChatOverlayChroma"
{
 Properties
 {
  _MainTex ("Font atlas", 2D) = "white" {}
  [HideInInspector] _MGFRSubtitleOpaquePanel ("Neutral key-camera panel", Float) = 0
 }
 SubShader
 {
  Tags { "Queue"="Overlay+1000" "RenderType"="Transparent" "IgnoreProjector"="True" }
  Cull Off ZWrite Off ZTest Always
  Blend SrcAlpha OneMinusSrcAlpha
  Pass
  {
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_instancing
#pragma multi_compile _ STEREO_INSTANCING_ON
#pragma multi_compile _ MGFR_BUILD_STEREO_VARIANT
   #include "UnityCG.cginc"
   struct appdata { float4 vertex:POSITION; float2 uv:TEXCOORD0; fixed4 color:COLOR; UNITY_VERTEX_INPUT_INSTANCE_ID };
   struct v2f { float4 vertex:SV_POSITION; float2 uv:TEXCOORD0; fixed4 color:COLOR; UNITY_VERTEX_OUTPUT_STEREO };
   sampler2D _MainTex; float _MGFRSubtitleOpaquePanel; float _MGFRRgbKeyCoverage;
   v2f vert(appdata v)
   {
    v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.vertex=UnityObjectToClipPos(v.vertex);o.uv=v.uv;o.color=v.color;return o;
   }
   fixed4 frag(v2f i):SV_Target
   {
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    fixed4 color=i.color;color.a*=tex2D(_MainTex,i.uv).a;
    // RGB-key streaming has no independent alpha channel. A neutral opaque UI plate
    // avoids mixing glyph edges with the key colour, including after 4:2:0 transport.
    // Text still uses its original antialiasing over this neutral plate.
    if(_MGFRRgbKeyCoverage>.5 && _MGFRSubtitleOpaquePanel>.5) color.a=1;
    return color;
   }
   ENDCG
  }
 }
}
