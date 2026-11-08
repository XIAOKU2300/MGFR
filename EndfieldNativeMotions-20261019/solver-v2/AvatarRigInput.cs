using System.Globalization;
using System.Numerics;
using System.Text.Json.Nodes;

namespace Ruri.RipperHook.Humanoid;

public sealed class AvatarRigInput
{
    public int[] NodeParent { get; init; }
    public int[] NodeAxesId { get; init; }

    public uint[] NodeId { get; init; }

    public AxesRow[] Axes { get; init; }

    public Dictionary<uint, string> Tos { get; init; }

    public int[] HumanBoneIndex { get; init; }
    public int[] LeftHandBoneIndex { get; init; }
    public int[] RightHandBoneIndex { get; init; }
    public float[] HumanBoneMass { get; init; }

    public Quaternion RootRestQ { get; init; }

    public float ArmTwist { get; init; }
    public float ForeArmTwist { get; init; }
    public float UpperLegTwist { get; init; }
    public float LegTwist { get; init; }

    public (Vector3 T, Quaternion Q)[] SkeletonPose { get; init; }

    public readonly record struct AxesRow(
        Quaternion PreQ, Quaternion PostQ, Vector3 Sgn, Vector3 LimitMin, Vector3 LimitMax);


    public static AvatarRigInput? FromDocumentJson(string avatarDocumentJson)
    {
        JsonNode? root = JsonNode.Parse(avatarDocumentJson);
        JsonNode? constant = Unwrap(root?["m_Avatar"]);
        JsonNode? human = Unwrap(constant?["m_Human"]);
        JsonNode? skeleton = Unwrap(human?["m_Skeleton"]);
        if (skeleton?["m_Node"] is not JsonArray nodes || nodes.Count == 0)
        {
            return null;
        }

        int[] nodeParent = new int[nodes.Count];
        int[] nodeAxesId = new int[nodes.Count];
        for (int i = 0; i < nodes.Count; i++)
        {
            nodeParent[i] = GetInt(nodes[i]?["m_ParentId"], -1);
            nodeAxesId[i] = GetInt(nodes[i]?["m_AxesId"], -1);
        }

        int[] rawIds = IntArray(skeleton["m_ID"]);
        uint[] nodeId = new uint[rawIds.Length];
        for (int i = 0; i < rawIds.Length; i++)
        {
            nodeId[i] = unchecked((uint)rawIds[i]);
        }

        AxesRow[] axes = skeleton["m_AxesArray"] is JsonArray axesArray
            ? axesArray.Select(ReadAxes).ToArray()
            : Array.Empty<AxesRow>();

        JsonNode? skeletonPose = Unwrap(human?["m_SkeletonPose"]);
        (Vector3, Quaternion)[] pose = skeletonPose?["m_X"] is JsonArray xforms
            ? xforms.Select(x => (GetVector3(x?["t"]), GetQuaternion(x?["q"]))).ToArray()
            : Array.Empty<(Vector3, Quaternion)>();

        JsonNode? rootX = human?["m_RootX"];

        return new AvatarRigInput
        {
            NodeParent = nodeParent,
            NodeAxesId = nodeAxesId,
            NodeId = nodeId,
            Axes = axes,
            Tos = ParseTos(root?["m_TOS"]),
            HumanBoneIndex = IntArray(human?["m_HumanBoneIndex"]),
            LeftHandBoneIndex = IntArray(Unwrap(human?["m_LeftHand"])?["m_HandBoneIndex"]),
            RightHandBoneIndex = IntArray(Unwrap(human?["m_RightHand"])?["m_HandBoneIndex"]),
            HumanBoneMass = FloatArray(human?["m_HumanBoneMass"]),
            RootRestQ = rootX is null ? Quaternion.Identity : GetQuaternion(rootX["q"]),
            ArmTwist = GetFloat(human?["m_ArmTwist"], 0.5f),
            ForeArmTwist = GetFloat(human?["m_ForeArmTwist"], 0.5f),
            UpperLegTwist = GetFloat(human?["m_UpperLegTwist"], 0.5f),
            LegTwist = GetFloat(human?["m_LegTwist"], 0.5f),
            SkeletonPose = pose,
        };
    }

    private static AxesRow ReadAxes(JsonNode? entry)
    {
        JsonNode? limit = entry?["m_Limit"];
        return new AxesRow(
            GetQuaternion(entry?["m_PreQ"]),
            GetQuaternion(entry?["m_PostQ"]),
            GetVector3(entry?["m_Sgn"], Vector3.One),
            GetVector3(limit?["m_Min"]),
            GetVector3(limit?["m_Max"]));
    }

    private static JsonNode? Unwrap(JsonNode? node)
    {
        while (node is JsonObject obj && obj.Count == 1 && obj.ContainsKey("data"))
        {
            node = obj["data"];
        }
        return node;
    }

    private static Dictionary<uint, string> ParseTos(JsonNode? tos)
    {
        Dictionary<uint, string> result = new();
        if (tos is JsonArray pairs)
        {
            foreach (JsonNode? pair in pairs)
            {
                if (pair is not JsonObject obj)
                {
                    continue;
                }
                JsonNode? key = obj["first"];
                JsonNode? value = obj["second"];
                if (value is null && obj.Count == 1)
                {
                    foreach (var kv in obj)
                    {
                        AddTos(result, kv.Key, kv.Value?.ToString());
                    }
                    continue;
                }
                AddTos(result, key?.ToString(), value?.ToString());
            }
        }
        else if (tos is JsonObject map)
        {
            foreach (var kv in map)
            {
                AddTos(result, kv.Key, kv.Value?.ToString());
            }
        }
        return result;
    }

    private static void AddTos(Dictionary<uint, string> result, string? key, string? path)
    {
        if (string.IsNullOrEmpty(path)
            || !long.TryParse(key, NumberStyles.Integer, CultureInfo.InvariantCulture, out long hash))
        {
            return;
        }
        result[unchecked((uint)hash)] = path;
    }

    private static readonly char[] HexDigits = "0123456789abcdefABCDEF".ToCharArray();

    private static int[] IntArray(JsonNode? node)
    {
        if (node is JsonArray list)
        {
            return list.Select(item => GetInt(item, 0)).ToArray();
        }
        string text = node?.ToString() ?? string.Empty;
        List<int> result = new(text.Length / 8);
        for (int i = 0; i + 8 <= text.Length; i += 8)
        {
            ReadOnlySpan<char> chunk = text.AsSpan(i, 8);
            bool hex = true;
            foreach (char c in chunk)
            {
                if (Array.IndexOf(HexDigits, c) < 0)
                {
                    hex = false;
                    break;
                }
            }
            if (!hex)
            {
                break;
            }
            uint big = uint.Parse(chunk, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            result.Add(unchecked((int)System.Buffers.Binary.BinaryPrimitives.ReverseEndianness(big)));
        }
        return result.ToArray();
    }

    private static float[] FloatArray(JsonNode? node)
    {
        if (node is JsonArray list)
        {
            return list.Select(item => GetFloat(item, 0f)).ToArray();
        }
        int[] bits = IntArray(node);
        float[] result = new float[bits.Length];
        for (int i = 0; i < bits.Length; i++)
        {
            result[i] = BitConverter.Int32BitsToSingle(bits[i]);
        }
        return result;
    }

    private static int GetInt(JsonNode? node, int fallback)
    {
        if (node is JsonValue value)
        {
            if (value.TryGetValue(out int direct))
            {
                return direct;
            }
            if (value.TryGetValue(out long wide))
            {
                return unchecked((int)wide);
            }
            if (value.TryGetValue(out double real))
            {
                return (int)real;
            }
            if (value.TryGetValue(out string? text)
                && long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out long parsed))
            {
                return unchecked((int)parsed);
            }
        }
        return fallback;
    }

    private static float GetFloat(JsonNode? node, float fallback)
    {
        if (node is JsonValue value)
        {
            if (value.TryGetValue(out double real))
            {
                return (float)real;
            }
            if (value.TryGetValue(out int direct))
            {
                return direct;
            }
            if (value.TryGetValue(out string? text)
                && double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out double parsed))
            {
                return (float)parsed;
            }
        }
        return fallback;
    }

    private static Vector3 GetVector3(JsonNode? node) => GetVector3(node, Vector3.Zero);

    private static Vector3 GetVector3(JsonNode? node, Vector3 fallback)
    {
        if (node is null)
        {
            return fallback;
        }
        return new Vector3(GetFloat(node["x"], 0f), GetFloat(node["y"], 0f), GetFloat(node["z"], 0f));
    }

    private static Quaternion GetQuaternion(JsonNode? node)
    {
        if (node is null)
        {
            return Quaternion.Identity;
        }
        return new Quaternion(GetFloat(node["x"], 0f), GetFloat(node["y"], 0f),
            GetFloat(node["z"], 0f), GetFloat(node["w"], 1f));
    }
}