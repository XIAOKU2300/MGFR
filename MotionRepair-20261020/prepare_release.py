"""Create the release package with isolated action-port support and catalog review."""
import prepare_candidate_v2
import prepare_candidate as build

original=build.make_sources
def make_sources(folder,repair):
    # All mutations happen in memory before any new destination is created.
    source_read=build.SOURCE
    class SourceProxy:
        def __truediv__(self,name):
            path=source_read/name
            if name!='MainAvatarActions.cs':return path
            class Source:
                def read_text(self,**kwargs):
                    text=path.read_text(**kwargs)
                    text=text.replace('tcp.Connect("127.0.0.1",18766);','tcp.Connect("127.0.0.1",bridgePort);')
                    text=text.replace('Host: 127.0.0.1:18766','Host: 127.0.0.1')
                    text=text.replace('  string root,json;','  int bridgePort=18766;\n  string root,json;')
                    text=text.replace('   Debug.Log("MAIN_INIT_STAGE audio");','   var cmd=Environment.GetCommandLineArgs();int portAt=Array.IndexOf(cmd,"-mgfr-action-port");if(portAt>=0&&portAt+1<cmd.Length)bridgePort=int.Parse(cmd[portAt+1]);\n   Debug.Log("MAIN_INIT_STAGE audio");')
                    text=text.replace('   if(Array.IndexOf(args,"-mgfr-actions-review")>=0)','   if(Array.IndexOf(args,"-mgfr-catalog-review")>=0)new GameObject("Catalog continuity review").AddComponent<MotionCatalogReview>();\n   if(Array.IndexOf(args,"-mgfr-actions-review")>=0)')
                    return text
            return Source()
    build.SOURCE=SourceProxy()
    try:original(folder,repair)
    finally:build.SOURCE=source_read
    build.create(folder/'MotionCatalogReview.cs',(build.ROOT/'MotionCatalogReview.cs').read_text(encoding='utf-8'))
build.make_sources=make_sources

if __name__=='__main__':build.main()
