using UnityEngine;

namespace MGFR.Dialogue
{
 public static class MicrophonePacket
 {
  public static byte[] Encode(float[] samples,int channels,int rate,uint round,ulong sequence)
  {
   int count=samples.Length/channels;var packet=new byte[24+count*2];packet[0]=1;packet[1]=1;
   Write(packet,4,round,4);Write(packet,8,sequence,8);Write(packet,16,(uint)rate,4);Write(packet,20,1,2);Write(packet,22,(ulong)(count*1000/rate),2);
   for(int i=0;i<count;i++)
   {
    float value=0;for(int c=0;c<channels;c++)value+=samples[i*channels+c];
    short pcm=(short)Mathf.RoundToInt(Mathf.Clamp(value/channels,-1,1)*32767);
    packet[24+i*2]=(byte)pcm;packet[25+i*2]=(byte)(pcm>>8);
   }
   return packet;
  }
  static void Write(byte[] data,int offset,ulong value,int count){for(int i=0;i<count;i++)data[offset+i]=(byte)(value>>(8*i));}
 }
}
