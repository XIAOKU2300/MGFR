Shader "Hidden/MGFR/ZmdComparison"
{
 Properties{_Before("Current",2D)="black"{} _After("ZMD",2D)="black"{}}
 SubShader
 {
  Cull Off ZWrite Off ZTest Always
  Pass
  {
   CGPROGRAM
   #pragma vertex vert_img
   #pragma fragment frag
   #include "UnityCG.cginc"
   sampler2D _Before,_After;
   fixed4 frag(v2f_img i):SV_Target
   {return i.uv.x<.5?tex2D(_Before,float2(i.uv.x*2,i.uv.y)):tex2D(_After,float2((i.uv.x-.5)*2,i.uv.y));}
   ENDCG
  }
 }
}
