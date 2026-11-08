# MGFR

<!-- impeccable:product-schema 1 -->

## Platform

Unity PCVR / OpenXR on Windows, with ALVR RGB chroma passthrough. This is a native spatial interface, not a web or mobile surface.

## Users and Purpose

The user interacts with an animated character by voice and tracked hands. Character motion, clothing physics, touch, pinching and wardrobe interaction must continue to work when the menu changes.

## Confirmed Menu Requirements

- Open the large spatial touch panel after a genuinely closed fist is continuously held for more than three seconds.
- Place it above the summoning hand, facing the user, then keep it fixed in world space. This anchoring was explicitly confirmed by the user.
- Use direct finger touch and generous control spacing. Show a short summon animation.
- Prevent gestures used to touch, grab or pull the character from summoning or operating the menu.
- Preserve the single existing launch entry and the voice configuration actually loaded by it.

## Existing Product Constraints

The verified current entry is `H:\MGFR\启动MGFR.cmd`, which loads `H:\MGFR\DialogueRenderRepair-20261020\launch_final.py` and the `Final-v3` player. Its active module source is in that player's sibling `Source` directory. Voice runs on 8776 and the action interface on 18769. These are live-verified paths, not conventions inferred from names.

Tracked hand input provides native joint poses and observation flags, separate from synthetic controller poses. Menu intent must use fresh native evidence. Clothing and character interaction already own hand-grab state; menu arbitration must preserve that ownership.

The scene uses a pure green key background. Opaque menu surfaces and antialiased text over those surfaces avoid repeating the previously fixed transparent subtitle problem. Do not add full-screen bloom, blur or tone mapping.

## Evidence and Open Decisions

The current menu implementation is `ControllerActions` plus `ControllerMenuView` in the Unity base project. Existing actions supply the starting control vocabulary.

The user confirmed world-fixed placement, then explicitly authorized completing the task and enabling it without further confirmation. Work proceeds through a runnable spatial implementation with desktop gesture replay and actual Unity rendering verification.

## Product Principles

- Intentional gestures outrank shortcuts.
- Failed or stale tracking cancels input rather than guessing.
- Readability, physical reach and target separation carry the visual design.
- Verify current runtime behavior and label synthetic versus headset evidence honestly.
