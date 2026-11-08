from pathlib import Path

lab=Path(__file__).resolve().parents[1]
s=(lab/'Source/WardrobeProbe2.cs').read_text(encoding='utf8').replace('public static class WardrobeProbe2','public static class WardrobeSupplement')
needle='                shot(id+"-01-equipped",new Vector3(0,.92f,-3),new Vector3(0,.92f,0));'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
                shot(id+"-back",new Vector3(0,.92f,3),new Vector3(0,.92f,0));
                shot(id+"-side",new Vector3(3,.92f,0),new Vector3(0,.92f,0));
                shot(id+"-threequarter",new Vector3(-2,.92f,-3),new Vector3(0,.92f,0));
                var anchors=new GameObject("Adapted garment grip anchors");
                var markerMaterial=new Material(loader.Materials[7]);markerMaterial.SetTexture("_MainTex",Texture2D.whiteTexture);
                markerMaterial.SetColor("_Color",new Color(1f,.35f,.04f));
                foreach(var part in adapter.Profile.parts)
                {
                    var marker=GameObject.CreatePrimitive(PrimitiveType.Sphere);marker.name=part.id;
                    marker.transform.SetParent(anchors.transform);marker.transform.position=adapter.AnchorWorld(part.id);
                    marker.transform.localScale=Vector3.one*.018f;marker.GetComponent<Renderer>().sharedMaterial=markerMaterial;
                }
                shot(id+"-grip-anchors",new Vector3(0,.92f,-3),new Vector3(0,.92f,0));
                UnityEngine.Object.DestroyImmediate(anchors);UnityEngine.Object.DestroyImmediate(markerMaterial);
''')
for p in (lab/'Source/WardrobeSupplement.cs',lab/'ProbeFinal/Assets/Editor/WardrobeSupplement.cs'):
    with p.open('x',encoding='utf8') as f:f.write(s)
print('Supplement source created; existing sources unchanged')
