---
name: MGFR Native Hand Panel
description: Opaque ceramic spatial controls with dark blue ink and tactile cyan state.
# CSS rgb percentages losslessly encode normalized C# Color input channels.
# They are not color-managed screenshot samples; read the native color rule below.
colors:
  accent: "rgb(0.8% 27% 38%)"
  selected: "rgb(65% 84% 88%)"
  contact-tint: "rgb(48% 76% 83%)"
  hold-fill: "rgb(40% 87% 95%)"
  ink: "rgb(2.6% 5% 7%)"
  muted: "rgb(20% 28% 33%)"
  ceramic: "rgb(84% 89% 92%)"
  chassis: "rgb(6.5% 10.5% 14%)"
  rule: "rgb(36% 48% 54%)"
  key-rest: "rgb(94% 96% 97%)"
  key-disabled: "rgb(74% 79% 82%)"
  ink-disabled: "rgb(32% 39% 43%)"
  caption-disabled: "rgb(34% 40% 43%)"
  switch-off: "rgb(43% 51% 55%)"
  hold-track: "rgb(10% 17% 21%)"
  hold-label: "rgb(100% 100% 100%)"
typography:
  title:
    fontFamily: "Microsoft YaHei"
    fontSize: "0.029 m"
    fontWeight: 400
    lineHeight: 1
  control:
    fontFamily: "Microsoft YaHei"
    fontSize: "0.020 m"
    fontWeight: 400
    lineHeight: 1
  compact:
    fontFamily: "Microsoft YaHei"
    fontSize: "0.016 m"
    fontWeight: 400
    lineHeight: 1
  caption:
    fontFamily: "Microsoft YaHei"
    fontSize: "0.0125 m"
    fontWeight: 400
    lineHeight: 1
  feedback:
    fontFamily: "Microsoft YaHei"
    fontSize: "0.012 m"
    fontWeight: 400
    lineHeight: 1
  hold:
    fontFamily: "Microsoft YaHei"
    fontSize: "0.015 m"
    fontWeight: 400
    lineHeight: 1
spacing:
  label-inset: "0.015 m"
  main-column-gap: "0.030 m"
  main-row-gap: "0.025 m"
  tab-gap: "0.025 m"
  touch-hit-inset: "0.004 m"
components:
  panel:
    backgroundColor: "{colors.ceramic}"
    textColor: "{colors.ink}"
    width: "0.680 m"
    height: "0.480 m"
  touch-key:
    backgroundColor: "{colors.key-rest}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    width: "0.277 m"
    height: "0.065 m"
  touch-key-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    width: "0.277 m"
    height: "0.065 m"
  touch-key-disabled:
    backgroundColor: "{colors.key-disabled}"
    textColor: "{colors.ink-disabled}"
    typography: "{typography.control}"
    width: "0.277 m"
    height: "0.065 m"
  page-target:
    backgroundColor: "{colors.key-rest}"
    textColor: "{colors.ink}"
    typography: "{typography.compact}"
    width: "0.184 m"
    height: "0.034 m"
  page-target-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.ink}"
    typography: "{typography.compact}"
    width: "0.184 m"
    height: "0.034 m"
  utility-key:
    backgroundColor: "{colors.key-rest}"
    textColor: "{colors.ink}"
    typography: "{typography.compact}"
    width: "0.277 m"
    height: "0.034 m"
  close-key:
    backgroundColor: "{colors.key-rest}"
    textColor: "{colors.ink}"
    typography: "{typography.compact}"
    width: "0.065 m"
    height: "0.047 m"
---

# Design System: MGFR Native Hand Panel

## Overview

**Creative North Star: "The Ceramic Control Console"**

The Ceramic Control Console is calm, solid and reachable. A cool light face carries dark blue labels, while small cyan marks and cyan-filled selected controls communicate state. A dark chamfered edge makes the panel readable against the passthrough scene without glass, bloom or a screen-wide treatment.

This document captures the implemented native Unity hand panel. It does not redefine the character, wardrobe or voice identity. Its reusable visual commitments are opaque surfaces, physical depth, readable Chinese text and separated touch targets; the exact page composition and gesture contract remain in .impeccable/surfaces/gesture-panel.md.

The descriptive name and color names are documentation language inferred from the approved direction and final rendered output. Source geometry and C# Color input channels are normative. Native captures establish appearance; sidecar previews are illustrative 2D translations.

**Key Characteristics:**

- Opaque cool ceramic with dark blue ink.
- Clipped chamfers and actual raised geometry.
- Cyan communicates selection, enabled switches and contact.
- Generous physical separation and explicit state captions.
- One native Microsoft YaHei text family.

## Colors

The palette combines pale ceramic neutrals, blue-black text and a single cyan state family.

The frontmatter encodes the exact normalized C# Color constructor channels as CSS rgb percentages: a percentage divided by 100 recovers its source channel. This is a portable input-token notation, not an assertion that Unity values are CSS sRGB or that they are all linear-sRGB. All source alpha values are 1. The shader bundle project uses Unity Linear color space (m_ActiveColorSpace: 1). Surface material colors and text vertex colors pass through different shaders; retain that distinction rather than applying one manual gamma conversion to every token.

### Primary

- **Deep Cyan Indicator** (accent): small enabled toggle markers.
- **Selected Ice Cyan** (selected): enabled switch faces and the selected page target.
- **Touch Cyan** (contact-tint): contact blend destination, not a separate resting button face.
- **Hold Cyan** (hold-fill): the small fist-hold progress fill before the panel opens.

### Neutral

- **Blue Black Ink** (ink): panel heading and enabled key labels.
- **Slate Caption** (muted): feedback and secondary state/detail lines.
- **Cool Ceramic** (ceramic): the opaque panel face.
- **Anodized Blue Edge** (chassis): dark physical chassis around the face.
- **Inset Slate Rule** (rule): the thin header rule.
- **Resting Porcelain** (key-rest): unselected and action key faces.
- **Disabled Ceramic**, **Disabled Slate Ink** and **Disabled Caption Slate** (key-disabled, ink-disabled, caption-disabled): unavailable control treatment.
- **Inactive Slate Marker** (switch-off): a toggle marker when off.
- **Hold Track Blue** and **Hold White** (hold-track, hold-label): the hold track and its instruction.

**The The Native Color Rule.** Preserve the C# Color input channels and the Unity shader path together. A browser swatch is not an appearance oracle for the Linear Unity player.

## Typography

**Text family:** Microsoft YaHei, loaded from the Windows OS by Unity. The implementation requests a dynamic atlas at 72 points with FontStyle.Normal, then scales the generated mesh into meters. It does not define a separate display face, fallback stack, bold weight or letter-spacing adjustment.

The frontmatter font sizes are nominal mesh text heights in native meters, not browser font sizes or guaranteed visible cap heights. TextGenerator uses lineSpacing 1 and MiddleLeft anchoring. Labels are single-line, left aligned and width-fitted by uniform scale reduction.

### Hierarchy

- **Title**: the panel heading, with maximum text width 0.460 m.
- **Control**: keys taller than 0.050 m; title maximum width equals key width minus 0.035 m.
- **Compact**: page, utility and close keys; the same width-fitting rule applies.
- **Caption**: the secondary line inside a main key.
- **Feedback**: the short instruction/status line under the heading, maximum width 0.530 m.
- **Hold**: the separate fist-hold instruction, maximum width 0.190 m.

Main-key labels sit 0.010 m above their key center when a caption exists. Captions sit 0.017 m below center. Keys without captions center their label vertically. Keep complete Chinese words and action/state meaning when shortening a label; the current implementation scales a long line down rather than wrapping it.

**The The Readable State Rule.** Keep the label, descriptive caption and toggle marker readable together; color alone does not carry a switch state.

## Layout

All geometry is specified in Unity meters. This is a spatial interface with a fixed physical composition; there are no browser breakpoints, mobile rearrangements or CSS pixel targets in the runtime.

The face dimensions, main targets and compact target dimensions are normative in the frontmatter. The dark chassis extends the face by 0.009 m in width and height. The header is above a three-target page row. Six main controls occupy two columns and three rows, followed by a separate utility row. Close occupies its own upper-right position. Exact current page placement belongs to the gesture-panel surface brief.

The main-column pitch is 0.307 m, and the main-row pitch is 0.090 m. Page-target pitch is 0.209 m. Text starts at the observed label inset. Hit regions are reduced by the touch-hit inset on all sides; visual gaps do not activate controls. The final native check measured a 0.025 m vertical gap and confirmed the central 0.030 m gap is inactive.

The panel is placed above the summoning palm, facing the user, then remains fixed in world space. Placement clamps horizontal reach to 0.46–0.85 m and height to the head's vertical position minus 0.30 m through plus 0.12 m. This reach behavior comes from runtime placement, not responsive scaling.

## Elevation & Depth

Depth is actual mesh geometry with subdued face-normal shading. There are no cast/received shadows on panel meshes and no CSS-like shadow vocabulary. The surface shader is opaque, writes depth and tests LEqual; its directional shade multiplier is 0.82 + 0.18 × saturate(dot(normal, normalized(-0.3, 0.6, -1))). Stereo instancing is compiled into both surface and text shaders.

The chassis is 0.018 m deep at local z 0.006 m. The ceramic face is 0.016 m deep at local z 0. A key is 0.012 m deep, based at local z -0.018 m. Its front interaction plane is z -0.024 m. On contact the key compresses toward the panel by up to 0.005 m; the position follows an exponential approach with rate 35 per second. The face tint blends toward contact-tint with a weight from 0.35 to 0.60, driven by fingertip compression.

The panel reveals and closes over 0.350 seconds using 1 - (1 - reveal)^3. Reveal travels upward by 0.040 m, settles an initial -8° tilt and scales from 0.92 to 1. Touch remains gated until reveal completes and the summoning fist is released. Subtitle renderers are temporarily suppressed while the panel is visible; their previous rendering flags are restored after the closing animation.

**The The Physical Depth Rule.** Depth comes from the chassis, raised keys and contact compression. Do not replace these with transparent glass or screen-wide effects.

## Shapes

The recurring silhouette is a straight-edged rectangle with clipped corners. These are chamfer cuts in an eight-vertex outline, not rounded radii; no rounded token scale is defined.

- Chassis corner cut: 0.014 m.
- Ceramic face corner cut: 0.012 m.
- All tactile key corner cuts: 0.004 m.
- Hold track, fill and switch marker corner cuts: 0.001 m, bounded by the mesh generator's cut limit.

The mesh generator caps the cut at 40% of the smaller half-dimension, so narrow indicators receive smaller effective cuts.

## Components

### Main touch key

A raised, chamfered physical target with one action label and, where present, one state/detail line. The resting, selected and disabled variants are specified in the frontmatter. Disabled controls are excluded from hit testing. Ordinary controls activate immediately when the fingertip volume crosses the front surface; swept intersection catches a fast poke even when the next sample is behind the panel. A sustained fingertip contact does not repeat. Withdraw the fingertip volume 0.010 m in front of the surface to rearm, with no additional waiting period. Recovery keeps its explicit 0.350-second hold. Touch uses the visible SDK hand pose and observed wrist/index, independently of the stricter whole-fist summon recognition.

### Toggle key

The main touch-key geometry plus a small state marker (0.012 × 0.004 × 0.001 m) near the upper-right corner. Enabled faces use selected with accent on the marker. Off faces use key-rest with switch-off on the marker. The caption provides the state in words. No sliding pill switch is implemented.

### Page targets

Three compact raised targets with a single centered-height, left-aligned label. Selected pages use the same selected face as enabled toggles, without the toggle marker. Current labels are 常用开关, 位置调整 and 大小与朝向.

### Utility and recovery keys

Compact raised controls below the main grid. The existing recovery label is 长按恢复穿戴 and requires a 0.350-second contact hold. 小球归位 uses the default contact hold. Their separate row preserves reach and helps distinguish recovery from repeated adjustment actions.

### Close key

An independent compact target labelled 收起, positioned in the header's upper-right. It uses the ordinary resting/contact treatment and runs the panel close animation.

### Hold progress indicator

A separate linear indicator appears above the fist only after progress exceeds 0.12 and while the panel is hidden. Its track is 0.160 × 0.005 × 0.002 m; its fill is 0.158 × 0.004 × 0.002 m and grows from the left. The instruction is 保持握拳. The completed summon requires more than three continuous seconds of valid, stable native fist evidence.

### Text mesh and state feedback

The custom text shader samples the dynamic font atlas alpha and blends glyphs over opaque panel surfaces. Live vocabulary is requested before UV meshes rebuild, and atlas repacking invalidates all labels. Preserve the complete-atlas rebuild contract when adding a page or changing copy.

The sidecar's five existing-control previews use a 1000 px/m drawing scale and approximate display colors. Browser hover/focus/active states are documentation aids, not native interaction modes.

## Do's and Don'ts

### Do:

- **Do** preserve native meter dimensions and the chamfered geometry when extending the panel.
- **Do** keep dark labels on opaque light faces and show the current state in text.
- **Do** keep touch targets separated by the implemented gaps and require retreat before another activation.
- **Do** preserve the selected page, disabled state and explicit close/recovery affordances.
- **Do** compare native rendered evidence when changing colors, font meshes or depth.

### Don't:

- **Don't** treat CSS preview pixels or browser focus behavior as the native PCVR implementation.
- **Don't** introduce transparent glass over the chroma-key scene, full-screen bloom, blur or tone mapping.
- **Don't** turn the controls into decorative floating cards or add unimplemented form inputs.
- **Don't** replace chamfer cuts with a rounded-pill visual language.
- **Don't** present synthetic desktop replay or rendered screenshots as headset validation.

Extraction sources: DialogueRenderRepair-20261020/Final-v3/Source/GesturePanel/GesturePanelVisual.cs, GesturePanel.shader, GesturePanelText.shader, GesturePanelRuntime.cs and HandMenuIntent.cs; PRODUCT.md; .impeccable/surfaces/gesture-panel.md. Native visual evidence: DialogueRenderRepair-20261020/Final-v3/MenuBuild/Review-20261020-205337-693030/Results (four Unity renders plus result.json). These captures use the actual Unity meshes/components with synthetic anatomical hand samples; they do not establish headset, microphone or remote LLM interaction.

