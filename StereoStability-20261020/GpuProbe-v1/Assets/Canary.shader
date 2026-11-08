Shader "Hidden/MgfrStereoCanary" {SubShader{Pass{Cull Off ZTest Always ZWrite Off HLSLPROGRAM
#pragma target 4.5
#pragma vertex vert
#pragma fragment frag
struct Out{float4 pos:SV_POSITION;uint eye:SV_RenderTargetArrayIndex;};
Out vert(uint vertex:SV_VertexID,uint instance:SV_InstanceID){Out o;float2 p=vertex==0?float2(-1,-1):vertex==1?float2(-1,3):float2(3,-1);o.pos=float4(p,0,1);o.eye=instance&1;return o;}
float4 frag(Out i):SV_Target{return float4(.8,.3,.2,1);}
ENDHLSL}}}