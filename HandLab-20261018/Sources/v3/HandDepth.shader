Shader "MGFR/HandDepth"
{
 Properties{_Tint("Debug colour",Color)=(.95,.55,.18,1) _WriteColor("Colour mask",Float)=0}
 SubShader
 {
  Tags{"Queue"="Geometry-100" "RenderType"="Opaque"}
  Pass
  {
   Cull Off ZWrite On ZTest LEqual ColorMask [_WriteColor]
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_instancing
   #include "UnityCG.cginc"
   float4 _Tint;
   struct appdata{float4 vertex:POSITION;UNITY_VERTEX_INPUT_INSTANCE_ID};
   struct v2f{float4 pos:SV_POSITION;UNITY_VERTEX_OUTPUT_STEREO};
   v2f vert(appdata v)
   {
    v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_OUTPUT(v2f,o);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.pos=UnityObjectToClipPos(v.vertex);return o;
   }
   float4 frag(v2f i):SV_Target{UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);return _Tint;}
   ENDCG
  }
 }
}
