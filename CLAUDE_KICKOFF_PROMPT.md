# Claude kickoff prompt

Read `CLAUDE.md`, `README.md`, and every document under `docs/` before writing code.

You are building MOTIONFORGE, an Android-first AI-assisted 3D workout and beginner fighting-fundamentals coach.

Follow the technical and product decisions in the repository. No Unity. Use Kotlin, Jetpack Compose, CameraX, MediaPipe Pose Landmarker, Room, and a verified Android-compatible GLB renderer. Blender is the source asset pipeline.

Start with Phase 0 from `docs/IMPLEMENTATION_PLAN.md`. First inspect the environment and verify current compatible dependency versions and APIs. Do not guess library APIs. Build technical spikes for:
1. Compose Android app scaffold.
2. CameraX preview.
3. MediaPipe pose processing on a sample frame.
4. Loading and playing one GLB animation.

Do not implement cloud AI or subscriptions yet. Keep guest/offline use working. Do not upload or save camera frames. Never fake pose tracking or claim medical/safety certainty.

After each phase, run available builds/tests, report exact outcomes, update `docs/BUILD_LOG.md`, and stop at the phase boundary for review. If a feature cannot be verified in the current environment, state what hardware/SDK/credential is missing and provide exact verification steps.
