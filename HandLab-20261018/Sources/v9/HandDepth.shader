Shader "MGFR/HandDepth"
{
 Properties{_Tint("Debug colour",Color)=(.55,.82,1,.36) _WriteColor("Colour mask",Float)=0}
 SubShader
 {
  Tags{"Queue"="Geometry-100" "RenderType"="Opaque"}
  Pass
  {
   Cull Off ZWrite On ZTest LEqual ColorMask [_WriteColor]
   Blend SrcAlpha OneMinusSrcAlpha
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_instancing
   #include "UnityCG.cginc"
   float4 _Tint;float _WriteColor;
   struct appdata{float4 vertex:POSITION;float3 normal:NORMAL;UNITY_VERTEX_INPUT_INSTANCE_ID};
   struct v2f{float4 pos:SV_POSITION;float3 normal:TEXCOORD0;UNITY_VERTEX_OUTPUT_STEREO};
   v2f vert(appdata v)
   {
    v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_OUTPUT(v2f,o);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.normal=UnityObjectToWorldNormal(v.normal);
    float3 world=mul(unity_ObjectToWorld,v.vertex).xyz;
    if(_WriteColor<1)world-=normalize(o.normal)*.0015;
    o.pos=mul(UNITY_MATRIX_VP,float4(world,1));return o;
   }
   float4 frag(v2f i):SV_Target
   {
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    float light=.65+.35*abs(dot(normalize(i.normal),normalize(float3(.3,.7,.6))));
    return float4(_Tint.rgb*light,_Tint.a);
   }
   ENDCG
  }
 }
}
