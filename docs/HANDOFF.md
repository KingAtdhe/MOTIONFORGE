# MOTIONFORGE — handoff notes (19 Nov 2026)

Read this first when continuing in a new chat. Then `CLAUDE.md`, `docs/BUILD_LOG.md`.

## Where things are
- Repo: `KingAtdhe/MOTIONFORGE` (branch `main`). Every push builds in GitHub Actions and republishes the
  debug APK: https://github.com/KingAtdhe/MOTIONFORGE/releases/download/debug-latest/motionforge-debug.apk
- App id `eu.motionforge.app`, single Gradle module `app/`, Kotlin 2.2.0, AGP 8.11.1, Gradle 8.14.3,
  compile/target SDK 36, min 26. Versions and reasons: `docs/DEPENDENCY_DECISIONS.md`.

## What is built
- Phase 0: CameraX + MediaPipe Pose Landmarker + Filament GLB spikes (Profile → Technical checks).
- Phase 1: onboarding (18+ gate, safety acknowledgement, focus, goal), Home, Train catalogue with filters,
  lesson detail, Profile, data reset. 9 lessons in `data/exercises.json` (= app asset; test keeps them equal).
- Phase 2: 3D trainer in lesson pages (play/pause, replay, 1×/0.5×/0.25×, front/side/back).
- Phases 3–5 slice: sessions (`feature/session`: SessionEngine, SessionPlanner, SessionScreen, SessionViewModel),
  optional camera with skeleton, experimental squat rep counter (`core/movement/SquatRepCounter`), summary,
  Room history (`core/database`), Progress screen.
- Design: Barlow / Barlow Condensed fonts, volt (#C8F542) = fitness, ember (#FF7A45) = fighting.
- 82 JVM unit tests.

## Trainer / coach model
- **Current in-app model (v5, 19 Nov):** female coach built from the owner's sheet
  `assets/blender/references/workout_coach_owner_sheet.png` (now in the repo). Pipeline in
  `tools/coach_from_sheet/` (see its README) + `tools/blender/build_coach_sheet.py`: body shape from the
  sheet's front + side outlines (outline overlap ~0.95 IoU), the owner's painting projected onto it
  (front/back/both sides, chest logo removed, 2048 JPEG texture), sculpted fist-capable hands, rig with finger
  bones, A-pose rest, the 9 clips. ~28.8k tris, GLB 1.8 MB, unlit materials. Paint source is a 4x-restored copy
  of the sheet (`esrgan.py`); gloves painted per vertex to match the sheet's glove detail. Side-by-side check:
  `assets/blender/references/coach_f_v5_vs_sheet.jpg`.
- Weak spots: painted detail is soft (sheet figures are ~420 px tall — a bigger sheet would sharpen it);
  smudges on the sides of the head/torso and inner thighs where no view saw the surface cleanly; hands are
  plain sculpted pieces next to the painted arms; ponytail is a simple lock; male coach not built.
- `build_coach.py` (procedural cel coach, v4) is kept for reference but **running it overwrites the in-app GLB**.

## Environment tricks that worked
- No Android SDK in the workspace; GitHub Actions is the compile check. Poll runs through
  `https://api.github.com/repos/KingAtdhe/MOTIONFORGE/actions/runs` and read job logs via `/actions/jobs/<id>/logs`.
- Pure-Kotlin logic + tests can be compiled locally with the Kotlin compiler bundled in Gradle
  (`/opt/gradle/lib/kotlin-compiler-embeddable-*.jar` + trove4j + annotations) and run with JUnit 4.
- Blender: `python -m venv bpyenv && bpyenv/bin/pip install bpy==5.3.0`, then run the build scripts with that
  Python (`import bpy` before `import bmesh`). Cycles CPU renders work headless.
- glTF check: `npm i gltf-validator`.

## Not verified / open
- Nothing has been confirmed on a real phone by measurement (inference ms, squat count accuracy, 3D frame rate).
- Squat counter thresholds are hypotheses; lesson text and all clips are drafts pending qualified-coach review.
- Sessions do not survive process death; no boxing-stance evaluator; no Supabase sync; no billing.
