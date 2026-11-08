using System.Collections.Generic;
using UnityEngine;

namespace MGFR.Character
{
    public sealed class ControllerMenuView : MonoBehaviour
    {
        const float Width = 720, Scale = .00078f;
        Font font;
        Material ink, paper;
        Mesh text, background;
        MeshRenderer textRenderer, backgroundRenderer;
        Transform root;
        readonly TextGenerator generator = new TextGenerator();
        readonly List<Vector3> positions = new List<Vector3>();
        readonly List<Vector2> uv = new List<Vector2>();
        readonly List<Color32> colors = new List<Color32>();
        readonly List<int> indices = new List<int>();
        string lastKey;
        bool atlasDirty;
        public bool Shown => root != null && root.gameObject.activeSelf;
        public int GlyphVertices => positions.Count;
        void Awake()
        {
            font = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 36);
            ink = new Material(Shader.Find("MGFR/ChatOverlay"));
            paper = new Material(ink); paper.mainTexture = Texture2D.whiteTexture;
            text = new Mesh { name = "Controller menu glyphs" };
            background = new Mesh { name = "Controller menu backing" };
            root = new GameObject("Headset controller quick menu").transform;
            textRenderer = MakeRenderer("Controller menu text", text, ink, 32767);
            backgroundRenderer = MakeRenderer("Controller menu backing", background, paper, 32766);
            Font.textureRebuilt += OnAtlas;
            Hide();
        }
        MeshRenderer MakeRenderer(string name, Mesh mesh, Material material, int order)
        {
            var go = new GameObject(name); go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = material;
            renderer.sortingOrder = order; renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false; return renderer;
        }
        void OnAtlas(Font changed) { if (changed == font) atlasDirty = true; }
        public void Show(string title, string[] rows, string help, string feedback)
        {
            if (root == null || Camera.main == null) return;
            if (root.parent != Camera.main.transform)
            {
                root.SetParent(Camera.main.transform, false);
                root.localPosition = new Vector3(.43f, .24f, 1.2f);
                root.localRotation = Quaternion.identity; root.localScale = Vector3.one * Scale;
            }
            root.gameObject.SetActive(true);
            string key = title + string.Join("\n", rows) + help + feedback;
            if (key == lastKey && !atlasDirty) return;
            lastKey = key;
            font.RequestCharactersInTexture(key, 36, FontStyle.Normal);
            font.RequestCharactersInTexture(key, 26, FontStyle.Normal);
            positions.Clear(); uv.Clear(); colors.Clear(); indices.Clear();
            Add(title, 30, -20, 36, new Color(.98f, .91f, .77f));
            float y = -88;
            foreach (string row in rows)
            {
                Add(row, 30, y, 36, row.StartsWith("▶") ? new Color(1f, .81f, .48f) : new Color(.96f, .97f, .98f));
                y -= 58;
            }
            Add(help, 30, y - 12, 26, new Color(.83f, .88f, .92f));
            Add(feedback, 30, y - 54, 26, new Color(.94f, .89f, .79f));
            float height = -y + 100;
            text.Clear(); text.SetVertices(positions); text.SetUVs(0, uv); text.SetColors(colors); text.SetTriangles(indices, 0); text.RecalculateBounds();
            ink.mainTexture = font.material.mainTexture;
            background.Clear();
            background.vertices = new[] { new Vector3(-Width / 2, 0, 1), new Vector3(Width / 2, 0, 1), new Vector3(Width / 2, -height, 1), new Vector3(-Width / 2, -height, 1) };
            background.uv = new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up };
            background.triangles = new[] { 0, 1, 2, 2, 3, 0 };
            var shade = new Color(.075f, .095f, .12f, .94f);
            background.colors = new[] { shade, shade, shade, shade };
            background.RecalculateBounds(); atlasDirty = false;
        }
        void Add(string value, float x, float y, int size, Color color)
        {
            var settings = new TextGenerationSettings { font = font, fontSize = size, fontStyle = FontStyle.Normal,
                color = color, lineSpacing = 1, richText = false, scaleFactor = 1, textAnchor = TextAnchor.UpperLeft,
                generationExtents = new Vector2(Width - 60, 1000), pivot = new Vector2(0, 1),
                horizontalOverflow = HorizontalWrapMode.Overflow, verticalOverflow = VerticalWrapMode.Overflow, updateBounds = true };
            generator.Populate(value, settings);
            var vertices = generator.verts;
            for (int i = 0; i + 3 < vertices.Count; i += 4)
            {
                int offset = positions.Count;
                for (int j = 0; j < 4; j++)
                {
                    var vertex = vertices[i + j]; positions.Add(new Vector3(vertex.position.x + x - Width / 2, vertex.position.y + y, 0));
                    uv.Add(vertex.uv0); colors.Add(vertex.color);
                }
                indices.Add(offset); indices.Add(offset + 1); indices.Add(offset + 2);
                indices.Add(offset + 2); indices.Add(offset + 3); indices.Add(offset);
            }
        }
        public void Hide() { if (root != null) root.gameObject.SetActive(false); }
        void OnDestroy()
        {
            Font.textureRebuilt -= OnAtlas;
            if (root != null) Destroy(root.gameObject);
            Destroy(ink); Destroy(paper); Destroy(text); Destroy(background); Destroy(font);
        }
    }
}
