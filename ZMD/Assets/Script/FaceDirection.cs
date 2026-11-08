using System.Collections;
using System.Collections.Generic;
using UnityEngine;

[ExecuteInEditMode]
public class FaceDirection : MonoBehaviour
{
    public Transform Head;
    public Transform HeadForward;
    public Transform HeadRight;
    public Transform HeadUp;
    public Material FaceMaterial;
    public Material HairMaterial;

    void Update()
    {
        if (Head == null) return;
        if (HeadForward == null) return;
        if (HeadRight == null) return;
        if (HeadUp == null) return;
        if (FaceMaterial == null) return;

        Vector3 headForward = Vector3.Normalize(HeadForward.position - Head.position);
        Vector3 headRight = Vector3.Normalize(HeadRight.position - Head.position);
        Vector3 headUp = Vector3.Normalize(HeadUp.position - Head.position);
        Vector3 headPosition = Head.position;

        // 设置为全局变量，供所有需要的 Shader 使用，保持原参数名不变
        Shader.SetGlobalVector("_HeadForward", headForward);
        Shader.SetGlobalVector("_HeadRight", headRight);
        Shader.SetGlobalVector("_HeadUp", headUp);
        Shader.SetGlobalVector("_HeadPosition", headPosition);
    }
}