# CORZA (formerly MOTIONFORGE) — Claude Development Package

**Product:** CORZA — AI Fitness & Boxing (working name MOTIONFORGE until 27 Nov 2026)  
**Category:** AI-assisted 3D fitness and fighting coach  
**Target:** Android first  
**Engine:** Native Android — Kotlin + Jetpack Compose  
**3D pipeline:** Blender → glTF/GLB → Android 3D renderer  
**Pose tracking:** MediaPipe Pose Landmarker  
**Backend:** Supabase (Postgres, Auth, Storage, Edge Functions)  
**No Unity.**

## What this package is

This is the product and engineering specification Claude should use to build MOTIONFORGE. It includes the product requirements, technical architecture, database schema, movement-analysis rules, Blender asset requirements, implementation sequence, QA plan, safety requirements, and acceptance criteria.

It is not a claim that a complete production-grade motion-coaching system can be created instantly or for less than €100. The budget target applies to a carefully scoped prototype using free/open-source tools and free tiers. Camera-based technique analysis needs real-world testing and must not be marketed as medical, injury-prevention, or professional coaching.

## Start here

1. Give Claude the entire extracted folder, preferably in a GitHub repository.
2. Tell Claude: **"Read CLAUDE.md and all referenced documents before coding. Follow the implementation order. Build the application in small, verifiable phases. Do not skip tests or replace working features with mock screens."**
3. Start with Phase 0 and Phase 1 in `docs/IMPLEMENTATION_PLAN.md`.
4. Commit after each phase.
5. Do not start subscription billing, cloud AI coaching, or complex fighting-style analysis until the core camera loop works reliably.

## Repository status

Phase 0 (technical foundation) is implemented. See `docs/BUILD_LOG.md` for what was verified and
how to test it on a phone, and `docs/DEPENDENCY_DECISIONS.md` for pinned versions.

### Build

Requirements: JDK 17, Android SDK (compileSdk 36). Network access on first build (Gradle
dependencies and the MediaPipe pose model).

```bash
./gradlew testDebugUnitTest      # JVM unit tests
./gradlew assembleDebug          # app/build/outputs/apk/debug/app-debug.apk
python3 tools/generate_spike_glb.py   # regenerate the Phase 0 test GLB
```

Every push to `main` builds in GitHub Actions and publishes the debug APK as the `debug-latest`
pre-release, so it can be installed directly on an Android phone.

## Core MVP promise

A user can:
- Choose a fitness or beginner striking session.
- View a realistic 3D trainer demonstrating a movement.
- Position their phone and grant camera permission.
- Receive on-device pose tracking and simple, explainable feedback.
- Complete a timed or repetition-based session.
- Review session history and basic progress.

The first MVP is an **exercise and beginner boxing fundamentals coach**, not a sparring simulator and not a replacement for a qualified coach.

## Product principles

- Safety before engagement.
- Honest feedback; never invent precision.
- On-device pose analysis where possible.
- No public user video uploads by default.
- Clear camera and data controls.
- No pay-to-win mechanics or manipulative streak pressure.
- Accessible instructions and beginner-friendly progression.
- Keep the first version small enough to test with real users.
