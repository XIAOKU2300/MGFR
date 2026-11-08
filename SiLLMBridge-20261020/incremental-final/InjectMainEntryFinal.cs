using System;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;
public static class InjectMainEntry {
 public static int Main(string[] args){
  if(args.Length!=4||File.Exists(args[2])||File.Exists(args[3]))throw new Exception("Expected source, plugin, NEW target, NEW report");
  var resolver=new DefaultAssemblyResolver();resolver.AddSearchDirectory(Path.GetDirectoryName(args[0]));resolver.AddSearchDirectory(Path.GetDirectoryName(args[1]));
  using(var original=ModuleDefinition.ReadModule(args[0],new ReaderParameters{AssemblyResolver=resolver}))using(var plugin=ModuleDefinition.ReadModule(args[1],new ReaderParameters{AssemblyResolver=resolver})){
   var type=original.Types.Single(t=>t.FullName=="MGFR.Character.SiCharacterBootstrap");var awake=type.Methods.Single(m=>m.Name=="Awake");
   var install=plugin.Types.Single(t=>t.FullName=="MGFR.StructuredVoiceFinal.MainAvatarActions").Methods.Single(m=>m.Name=="Install");if(!install.IsPublic||!install.IsStatic)throw new Exception("Entry must be public static");
   var returns=awake.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ret).ToArray();if(returns.Length!=1)throw new Exception("Unexpected Awake IL");
   var before=awake.Body.Instructions.Select(i=>i.ToString()).ToArray();awake.Body.GetILProcessor().InsertBefore(returns[0],Instruction.Create(OpCodes.Call,original.ImportReference(install)));
   using(var stream=new FileStream(args[2],FileMode.CreateNew))original.Write(stream);
   using(var writer=new StreamWriter(new FileStream(args[3],FileMode.CreateNew))){writer.WriteLine("Managed .NET module confirmed: "+original.Name);writer.WriteLine("Only method changed: "+awake.FullName);writer.WriteLine("Inserted one call to new opt-in Install before existing return. All existing methods/assets retained.");writer.WriteLine("Before:");foreach(var i in before)writer.WriteLine(i);writer.WriteLine("After:");foreach(var i in awake.Body.Instructions)writer.WriteLine(i);}
  }return 0;
 }
}
