using System;
using UnityEngine;
namespace MGFR.Dialogue
{
 public static class ChatBuild
 {
  public static void Build()
  {
   foreach(var name in new[]{"MGFR/ChatOverlay","Unlit/Color"})
   {
    var result=MGFR.EditorTools.MgfrEditorMenu.EnsureAlwaysIncludedShader(name);
    if(!result.StartsWith("added",StringComparison.Ordinal)&&!result.StartsWith("already",StringComparison.Ordinal))throw new Exception(result);
   }
   VoiceExperienceBuild.Build();
  }
 }
}
