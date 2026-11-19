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
- Current in-app model: female coach built by `tools/blender/build_coach.py` (run with `--previews`), following
  the owner's "Workout Coach" reference sheet (no "W" logo). Muscle-form clay blockout → voxel remesh →
  cavity paint → auto weights → garments cut from body → head/face parts, hair, hands, gloves, trainers →
  cel shading baked into vertex colours (COLOR_0), all materials `KHR_materials_unlit`, inverted-hull outline.
  ~35k tris (was 64k). Rig/clips: `trainer_rig.py` (25 bones incl. `fingers_*`/`fingertips_*`), `trainer_anim.py`
  (9 clips, no push-up; fists in all boxing clips, relaxed hands otherwise; footwork uses two-bone leg IK so the
  standing foot stays planted). Clothing is painted on the body faces along bisect loops (clean hems), abs are
  painted lines on a flat rectus plate. Fast iteration: `build_coach.py --previews --quick` (5 small renders, ~1 min).
- Sheet of renders: `python tools/blender/compose_coach_sheet.py` → `assets/blender/references/coach_f_3d_concept_sheet.jpg`.
- Fixed 19 Nov: ragged hems, lumpy abs, heavy lips/nose, no fists, foot sliding, polycount.
- Known weak spots: still a stylised procedural figure, not her painted sheet's level; boxy shoulders; outline
  hull streaks at sharply bent elbows; no facial expressions; male coach not built.
- Older scripts kept: `build_trainer.py` (mannequin), `tools/art/trainer_model_sheet.py` (vector sheets, rejected).
- Owner's reference image was sent in chat only; it is NOT in the repo — ask her to re-attach it.

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
