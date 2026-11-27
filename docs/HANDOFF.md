# MOTIONFORGE — handoff notes (updated 27 Nov 2026)

Read this first when continuing in a new chat. Then `CLAUDE.md` and the newest entries of `docs/BUILD_LOG.md`
(the log is in date order; everything below is a summary of it).

## Where things are
- Repo: `KingAtdhe/MOTIONFORGE` (branch `main`, work lands through PRs). Every push to `main` builds in GitHub Actions
  and republishes the debug APK: https://github.com/KingAtdhe/MOTIONFORGE/releases/download/debug-latest/motionforge-debug.apk
- App id `eu.motionforge.app`, single Gradle module `app/`, Kotlin 2.2.0, AGP 8.11.1, Gradle 8.14.3,
  compile/target SDK 36, min 26. Versions and reasons: `docs/DEPENDENCY_DECISIONS.md`.
- Screenshots of the main screens: `ci-screenshots` branch (refreshed by every CI run on `main`).

## What is built (as of 27 Nov)
- **Catalogue:** 128 lessons in `data/exercises.json` (= the app asset; a test keeps them equal), fitness and
  fighting fundamentals, search bar, filters. Every lesson has a 3D demo on both coaches.
- **Coaches:** female and male, from the owner's Tripo meshes (Mixamo-style rig), chosen from the gender asked in
  onboarding / Profile → "Your coach". Clips are authored in `tools/blender/authored_clips.py` and the `clips_*.py`
  batches (fists when punching), checked with the QC tools in `tools/qc/` and motion-study renders
  (`render_studies.py` + `compose_studies.py`).
- **Sessions:** guided workouts with timer, voice coach (Android TTS), optional camera with skeleton; a workout
  survives the app being closed (`ActiveSessionStore` snapshot); summary, Room history, Progress (incl. hold times).
- **Live camera coaching** for most lessons: rep counters (`core/movement`), hold checks (`HoldChecks.kt`), boxing
  stance/jab/cross rules and the guard check. Lessons without a check are `analysisMode: guided_not_scored`
  (warm-up march, footwork drills by spec, the standing quad stretch). All thresholds are validated on rendered
  videos of the coaches (`RenderedVideoRepTest`, fixtures in `app/src/test/resources/pose_fixtures/`).
- **Plans and build-your-own:** 6 plans, build-your-own sessions by focus / length / equipment with levels 1–3,
  shadow-boxing rounds with a bell and called combinations, cool-down stretches.
- **Reminders:** optional, off by default (Profile → Reminders).
- **Languages:** all 24 EU languages (Profile → Language), translation tables in `assets/i18n/<lang>.json`,
  machine-translated and not reviewed by native speakers. New text: `python3 tools/i18n/extract.py`, translate,
  `python3 tools/i18n/check.py`.
- **Name:** CORZA since 27 Nov 2026 (BUILD_LOG 27 Nov (9), docs/STORE_LISTING.md); app ID and packages stay `eu.motionforge.app`.
- **Design:** v5 "motion lab" (see BUILD_LOG 22 Nov). Icon and launch screen v6 from the owner's flexing-poses art (BUILD_LOG 27 Nov (8), `tools/branding_v6`).

## Rendered-video pose tests (how the camera checks are validated)
1. Blender: `python3 -m venv bpyenv && bpyenv/bin/pip install bpy==5.3.0 mediapipe pillow numpy`.
2. Pose model: not downloadable here (storage.googleapis.com is blocked); take `assets/models/pose_landmarker_lite.task`
   from the published debug APK (download the release asset through the GitHub REST API).
3. `tools/pose_tests/render_video.py <coach.glb> <out_dir> <view> "<clip sequence>" <fps>` renders a phone-like video;
   `tools/pose_tests/landmarks.py <dir> <out.lm>` runs the app's pose model over it (VIDEO mode, like the app).
   `batch.sh` wraps both. Gzip the `.lm` into `pose_fixtures/` and add a line to `expected.txt`.
4. Always add negatives (standing still, marching, boxing stance, other lessons' videos) that must count / hold nothing.

## Environment tricks that worked
- No Android SDK in the workspace; GitHub Actions is the compile check (REST API only: `gh api repos/...`; GraphQL
  and `gh release download` are blocked, use `gh api -H "Accept: application/octet-stream" .../releases/assets/<id>`).
- Pure-Kotlin logic + tests can be compiled locally with the Kotlin compiler bundled in Gradle
  (`/opt/gradle/lib/kotlin-compiler-embeddable-*.jar` + trove4j + annotations) and run with JUnit 4.
- glTF check: `npm i gltf-validator`.

## Not verified / open
- Nothing has been confirmed on a real phone by measurement (inference ms, count accuracy, 3D frame rate).
- Lesson text, clips and all camera thresholds are drafts pending qualified-coach review.
- Translations need native-speaker review.
- No Supabase sync, no billing.
