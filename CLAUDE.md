# CLAUDE.md — MOTIONFORGE Project Instructions

You are the senior Android engineer, technical lead, QA engineer, and implementation partner for MOTIONFORGE.

## Mandatory first steps

Before editing code:
1. Read `README.md`.
2. Read every file in `docs/`.
3. Read `database/schema.sql` and the JSON exercise data in `data/`.
4. Inspect the repository and identify existing code before changing it.
5. Produce a short implementation plan for the current phase.
6. Ask only if a decision blocks safe or correct implementation. Otherwise follow this specification.

## Non-negotiable constraints

- Android-first.
- Kotlin and Jetpack Compose.
- No Unity, Unreal, or game engine.
- Blender is the 3D creation tool.
- Use MediaPipe Pose Landmarker for the first on-device pose-tracking implementation.
- Use a maintained Android-compatible glTF/Filament-based renderer for 3D GLB assets. Verify the current library/API version before integrating; do not invent APIs.
- Use Supabase for optional account sync and backend services. Core demo/training flows should work locally without login.
- Do not put secrets, service-role keys, or private API keys in the Android app.
- Do not upload camera frames or video by default.
- Do not claim that the application diagnoses injuries, prevents injuries, certifies technique, or replaces an in-person instructor.
- Do not generate fake tracking results. If tracking is unavailable, show a clear unavailable/calibration state.
- Do not ship placeholder buttons that appear functional but do nothing.
- Keep architecture modular and testable.
- Use current stable dependency versions compatible with the installed Android Gradle Plugin and Kotlin version. Record versions in the version catalog.
- Never silently downgrade security, privacy, or safety requirements to make a demo work.

## Product scope

The MVP includes:
- Onboarding and clear safety notice.
- Local guest mode.
- Training category selection: Fitness / Fighting Fundamentals.
- Exercise and lesson catalogue.
- Exercise detail with instructions, common mistakes, and 3D demonstration.
- Camera permission and camera setup.
- Live pose landmark display for supported movements.
- Rule-based feedback for a small, validated movement set.
- Workout/session timer and repetition tracking where reliable.
- Session summary and local progress history.
- Settings for camera, privacy, units, and data deletion.
- Optional Supabase authentication and sync only after local MVP is stable.

MVP movement set:
- Bodyweight squat.
- Hip hinge pattern (instructional only until validated).
- Push-up (camera angle dependent; provide setup guidance).
- Boxing stance.
- Jab.
- Cross.
- Basic guard return.
- Basic forward/backward footwork as a guided drill, not automatic quality scoring.

Do not add kicks, sparring, partner drills, complex combinations, or advanced martial arts scoring in the first release.

## Engineering workflow

For each phase:
1. State the files you will create/change.
2. Implement a small vertical slice.
3. Build the Android app.
4. Run unit tests and relevant instrumentation tests.
5. Report actual build/test outcomes; never claim tests passed if not run.
6. Fix compiler errors before proceeding.
7. Update `docs/BUILD_LOG.md` with completed work, decisions, and known issues.
8. Commit-ready changes only; do not mix unrelated refactors.

When a build/test cannot run because the environment lacks Android SDK, emulator, camera, or credentials, state exactly what could not be verified and provide reproducible steps.

## Architecture expectations

Use clean, pragmatic layers:
- `app`: navigation, application setup, dependency injection.
- `core:model`: domain models.
- `core:database`: Room/local persistence.
- `core:camera`: CameraX lifecycle and frame pipeline.
- `core:pose`: MediaPipe integration and landmark models.
- `core:render3d`: GLB loading and animation playback.
- `core:design`: reusable Compose components and theme.
- `feature:onboarding`
- `feature:home`
- `feature:catalog`
- `feature:session`
- `feature:progress`
- `feature:settings`
- `data`: repositories and optional Supabase adapters.

Avoid premature microservices. A modular Android app is enough.

## Pose-analysis rules

- Keep raw camera frames in memory only unless a user explicitly chooses a future opt-in recording feature.
- Prefer processing on device.
- Use confidence thresholds and reject low-confidence landmarks.
- Normalize coordinates and account for mirrored preview versus actual camera coordinates.
- Use smoothing carefully; avoid hiding sudden unsafe movement.
- Feedback must be tied to measurable rules and show uncertainty when applicable.
- Do not infer pain, injury, health status, or medical conditions.
- Do not score movements if the camera view is unsuitable or the body is occluded.
- Never give high-confidence feedback from a single low-quality frame.
- Start with a neutral status: "Move into view", "Adjust camera", "Hold position", "Tracking", "Unable to assess".
- Use "possible form adjustment" language rather than absolute claims.

## 3D asset rules

- Blender source files must be retained in `assets/blender/`.
- Export delivery assets as `.glb`.
- Use consistent scale, origin, naming, skeleton hierarchy, animation names, and frame rate.
- Include a static fallback illustration/video-free explanation if 3D rendering is unavailable.
- Keep 3D models optimized for mid-range Android devices.
- Do not use copyrighted characters, branded sportswear, or copied likenesses.

## Security and privacy

- Request camera permission only when the user enters a camera-based session.
- Explain why permission is needed before the system prompt.
- No camera access in background.
- No video upload in MVP.
- Store only necessary session metrics.
- Add account deletion and local data reset.
- Use Supabase Row Level Security for all user-owned rows.
- Do not store authentication tokens in plaintext custom storage.
- Never log frames, images, access tokens, or sensitive user data.

## Definition of done

A feature is done only when:
- It builds.
- It has relevant tests.
- Empty, loading, error, and permission-denied states exist.
- It works on a real Android device or has clearly documented device-test limitations.
- Accessibility labels and touch targets are reasonable.
- It respects privacy and safety requirements.
- Documentation is updated.
