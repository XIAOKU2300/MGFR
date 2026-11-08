Shader "MGFR/ChatOverlayChroma"
{
 Properties
 {
  _MainTex ("Font atlas", 2D) = "white" {}
  [HideInInspector] _SrcBlend ("Source blend", Float) = 5
  [HideInInspector] _DstBlend ("Destination blend", Float) = 10
  [HideInInspector] _KeyCoverage ("RGB key coverage", Float) = 0
 }
 SubShader
 {
  Tags { "Queue"="Overlay+1000" "RenderType"="Transparent" "IgnoreProjector"="True" }
  Cull Off ZWrite Off ZTest Always
  Blend [_SrcBlend] [_DstBlend]
  Pass
  {
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_instancing
   #include "UnityCG.cginc"
   struct appdata { float4 vertex:POSITION; float2 uv:TEXCOORD0; fixed4 color:COLOR; UNITY_VERTEX_INPUT_INSTANCE_ID };
   struct v2f { float4 vertex:SV_POSITION; float2 uv:TEXCOORD0; fixed4 color:COLOR; UNITY_VERTEX_OUTPUT_STEREO };
   sampler2D _MainTex; float _KeyCoverage;
   v2f vert(appdata v)
   {
    v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.vertex=UnityObjectToClipPos(v.vertex);o.uv=v.uv;o.color=v.color;return o;
   }
   float CoverageThreshold(float2 pixel)
   {
    uint2 p = (uint2)floor(pixel) & 3u;
    // Stable screen-space Bayer coverage: output is source colour or untouched key.
    const float table[16] = {0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5};
    return (table[p.y*4u+p.x]+.5)/16.0;
   }
   fixed4 frag(v2f i):SV_Target
   {
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    fixed4 color=i.color;color.a*=tex2D(_MainTex,i.uv).a;
    if(_KeyCoverage>.5)
    {
     clip(color.a-CoverageThreshold(i.vertex.xy));
     return fixed4(color.rgb,1);
    }
    return color;
   }
   ENDCG
  }
 }
}
