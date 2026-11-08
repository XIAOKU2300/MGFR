#ifndef MGFR_COVERAGE_INCLUDED
#define MGFR_COVERAGE_INCLUDED
#include "UnityCG.cginc"
#ifndef MGFR_CAMERA_DEPTH_DECLARED
#define MGFR_CAMERA_DEPTH_DECLARED
UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
#endif
float _MGFRRgbKeyCoverage;
float _MGFRRgbKeyCoverageCell;
float _MGFRDepthCoverageAvailable;
float2 MgfrCoverageUV(float2 uv, float2 pixel)
{
    return uv; // no screen-space block sampling
}
float MgfrCoverageAlpha(float alpha, float2 pixel)
{
    if (_MGFRRgbKeyCoverage < .5) return alpha;
    // Retain real translucency over opaque character geometry. At the silhouette
    // there is only the RGB key, so use a continuous foreground, never a Bayer grid.
    clip(saturate(alpha) - .02);
    if (_MGFRDepthCoverageAvailable > .5)
    {
        float2 uv = UnityStereoTransformScreenSpaceTex(pixel / _ScreenParams.xy);
        float depth = SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture, uv);
        if (Linear01Depth(depth) < .9999) return alpha;
    }
    return 1;
}
#endif
