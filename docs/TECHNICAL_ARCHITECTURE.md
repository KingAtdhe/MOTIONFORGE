# MOTIONFORGE — Technical Architecture

## 1. Platform decision

Use a native Android application built with:
- Kotlin
- Jetpack Compose
- Android Gradle Plugin
- CameraX
- MediaPipe Tasks Vision Pose Landmarker
- Room for local persistence
- Kotlin Coroutines and Flow
- A maintained Android GLB/glTF renderer based on Filament (select and verify the current compatible library during Phase 0)
- Supabase for optional account sync/backend

No Unity or Unreal.

### Why native Android
Camera lifecycle, frame processing, permissions, and on-device inference are central to the product. Native Android reduces the need to bridge complex camera and ML components through a cross-platform layer.

## 2. High-level architecture

Compose UI
  ↓
Feature ViewModels
  ↓
Domain use cases
  ↓
Repositories
  ├── Room local database
  ├── CameraX frame source
  │     ↓
  │   Pose Landmarker
  │     ↓
  │   Landmark normalization/smoothing
  │     ↓
  │   Movement rule evaluator
  ├── 3D renderer / GLB animation player
  └── Supabase remote adapter (optional)

## 3. Suggested module structure

```text
motionforge/
  app/
  core/
    model/
    design/
    database/
    camera/
    pose/
    movement/
    render3d/
    common/
  data/
    repository/
    remote/
  feature/
    onboarding/
    home/
    catalog/
    lesson/
    session/
    progress/
    settings/
  assets/
    exercise_data/
    models/
  docs/
```

A single Gradle app module is acceptable for the first scaffold if Claude can keep package boundaries clean. Split into Gradle modules only when integration becomes clearer.

## 4. Camera pipeline

- Use CameraX Preview + ImageAnalysis.
- Bind camera use cases to lifecycle.
- Use a single-thread executor for image analysis.
- Set backpressure strategy to KEEP_ONLY_LATEST.
- Close every ImageProxy in a finally block.
- Convert frames correctly for MediaPipe.
- Respect rotation metadata and front-camera mirroring.
- Limit inference rate to a target suitable for mid-range devices (initial target 10–20 FPS; measure).
- Never block the main thread.
- Do not save frames to disk.

## 5. Pose model

Use MediaPipe Pose Landmarker with a compatible model asset. Verify the current Android API, model bundle, licensing, and dependency compatibility before implementation.

Internal landmark model should contain:
- landmark identifier
- x/y/z normalized values
- visibility/presence confidence
- frame timestamp
- image dimensions
- camera orientation/mirror metadata

Do not expose raw MediaPipe types outside the pose module.

## 6. Movement analysis

Use deterministic, explainable rules for MVP. Example:
- Compute joint angles from 2D/3D landmark vectors.
- Require landmark visibility above a threshold.
- Smooth noisy values over a short rolling window.
- Track movement phases with a finite-state machine.
- Count a repetition only after a valid down/up cycle.
- Add cooldown/debounce to avoid duplicate counts.
- If the user leaves frame or confidence falls, pause evaluation.
- Feedback must be based on a rule and show its limitation.

Never use a generic LLM as the real-time biomechanics engine.

## 7. 3D rendering

- Import optimized GLB files.
- Use a consistent avatar rig.
- Play named animation clips.
- Provide orbit/rotation only on lesson detail screens.
- During sessions, keep controls simple and performance stable.
- Include a static image/text fallback if rendering fails.
- Load large assets asynchronously.
- Cache assets locally after first successful download if remote delivery is used.

## 8. Backend

Supabase is optional in MVP. Local guest mode must work.

Potential remote features:
- Authentication.
- Profile sync.
- Programme catalogue.
- Content metadata.
- Subscription entitlement verification (later).
- Anonymous aggregate product analytics only with appropriate disclosure/consent.

Do not upload pose landmarks or video in MVP. If future sync of derived metrics is added, document each metric and obtain user consent.

## 9. Offline-first

The user should be able to:
- Open the app.
- View downloaded lessons.
- Play bundled 3D demos.
- Complete local sessions.
- View local progress.

Network should only be needed for optional account sync, catalogue updates, and future purchases.

## 10. Performance targets (to validate)

- Smooth UI on representative mid-range Android devices.
- Avoid sustained camera inference that overheats devices.
- Target 10–20 pose inferences per second initially.
- Keep UI responsive when camera inference is active.
- Reduce inference rate or resolution on thermal/performance pressure.
- 3D assets should be optimized for mobile memory and GPU limits.

These are engineering targets, not guaranteed performance claims.
