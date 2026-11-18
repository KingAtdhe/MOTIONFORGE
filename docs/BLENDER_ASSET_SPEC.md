# Blender Asset Production Specification

## 1. Visual direction

- Realistic, approachable human trainers.
- Premium sports-science presentation, not an aggressive combat-game aesthetic.
- Neutral studio/gym environment.
- Clear silhouette and readable joint movement.
- Inclusive trainer options can be added after the first asset pipeline is stable.
- No real-person likenesses without explicit rights.

## 2. MVP deliverables

### Avatar
- One neutral adult trainer avatar.
- Full body.
- Neutral A-pose or T-pose agreed with rig.
- Clean topology and deformation.
- Separate clothing materials if useful.
- No unnecessary high-poly details.
- Mobile-optimized textures.

### Environment
- One neutral studio background.
- Simple floor plane and soft lighting.
- Avoid complex dynamic shadows in the first release.

### Animation clips
Each clip must have consistent naming:
- `idle_neutral`
- `squat_down`
- `squat_up`
- `pushup_down`
- `pushup_up`
- `boxing_stance`
- `boxing_jab`
- `boxing_cross`
- `boxing_guard_return`
- `footwork_forward`
- `footwork_backward`

Only deliver clips that have been reviewed for instructional quality by a qualified coach.

## 3. Rig requirements

- One consistent humanoid skeleton.
- Stable bone naming.
- Correct bone roll and hierarchy.
- Root motion disabled unless explicitly required.
- Animation origin centered consistently.
- No scale animation on the armature.
- Export GLB with animations.
- Test in an external glTF viewer before Android integration.

## 4. Export settings

- Format: glTF Binary (.glb).
- Apply transforms.
- Use consistent metric scale.
- Export only required meshes, armature, materials and animation clips.
- Compress textures appropriately.
- Keep texture resolution modest for Android.
- Remove hidden geometry and unused objects.
- Verify animation names and frame ranges after export.

## 5. Suggested asset directory

```text
assets/
  blender/
    source/
      trainer_avatar.blend
      training_studio.blend
    exports/
      trainer_avatar.glb
      training_studio.glb
    previews/
  references/
  licenses/
```

## 6. Quality checklist

- Avatar proportions look natural.
- Feet do not slide during static demonstrations unless intended.
- Hands and elbows deform cleanly.
- No mesh intersections in key poses.
- Animation starts/ends at expected positions.
- Camera views show the relevant body parts.
- Animation remains readable at slow speed.
- GLB loads on a mid-range Android device.
- Source `.blend` files are retained.
- Asset origin and usage rights are documented.
