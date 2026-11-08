Shader "EndfieldNative/Preview" {
 Properties {_MainTex("Native albedo",2D)="white"{} _Color("Tint",Color)=(1,1,1,1) _Cutoff("Alpha cutoff",Float)=0 _Src("Source blend",Float)=1 _Dst("Destination blend",Float)=0}
 SubShader { Tags {"RenderType"="Opaque"} Cull Off ZWrite On Blend [_Src] [_Dst]
  Pass { CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #include "UnityCG.cginc"
   sampler2D _MainTex;float4 _MainTex_ST,_Color;float _Cutoff;
   struct app {float4 vertex:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;};struct vary {float4 pos:SV_POSITION;float2 uv:TEXCOORD0;float3 normal:TEXCOORD1;};
   vary vert(app v){vary o;o.pos=UnityObjectToClipPos(v.vertex);o.uv=TRANSFORM_TEX(v.uv,_MainTex);o.normal=UnityObjectToWorldNormal(v.normal);return o;}
   float4 frag(vary i):SV_Target {float4 c=tex2D(_MainTex,i.uv)*_Color;clip(c.a-_Cutoff);float shade=.76+.24*saturate(dot(normalize(i.normal),normalize(float3(-.4,.8,.7))));c.rgb*=shade;return float4(c.rgb,1);}
  ENDCG }
 }
}
