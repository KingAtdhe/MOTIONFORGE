# Dependency & Version Decisions (Phase 0)

Recorded 2026-11-18. All versions live in `gradle/libs.versions.toml`.

## How versions were chosen

The Phase 0 workspace had **no Android SDK and no access to Google Maven / Maven Central**, so
versions could not be resolved locally. The rule applied: pin **known-published, mutually
compatible stable releases** (prefer a proven combination over the newest number), let CI
(GitHub Actions, which has full network access) be the build verifier, and let Dependabot
propose upgrades that must pass CI before merging. Newer stable lines exist at the time of
writing (e.g. AGP 9.x, CameraX 1.6.x) and are deliberately deferred — see "Upgrade path".

| Component | Version | Notes |
|---|---|---|
| Gradle | 8.14.3 | Wrapper committed. |
| Android Gradle Plugin | 8.11.1 | Supports compileSdk/targetSdk 36. AGP 9 changes the DSL (built-in Kotlin, new variant API); deferred until the core loop is stable. |
| Kotlin | 2.2.0 | With the Compose compiler plugin of the same version. |
| compileSdk / targetSdk / minSdk | 36 / 36 / 26 | minSdk 26 keeps CameraX, MediaPipe and Filament well inside their supported ranges. |
| Compose BOM | 2025.06.01 | Material 3, icons-core. |
| activity-compose / lifecycle / navigation-compose | 1.10.1 / 2.9.1 / 2.9.0 | String routes (no serialization plugin needed). |
| CameraX | 1.4.2 | Preview + ImageAnalysis, `ImageProxy.toBitmap()`, `ResolutionSelector`. |
| MediaPipe Tasks Vision | 0.10.26 | Pose Landmarker, LIVE_STREAM mode. 0.10.26 release notes state its Android packages support 16 KB pages. |
| Pose model | `pose_landmarker_lite.task` float16 v1 | Downloaded at build time from Google's model bucket (Apache-2.0); not committed. |
| 3D renderer | Filament 1.71.4 (`filament-android`, `gltfio-android`, `filament-utils-android`) | See below. |
| kotlinx-serialization-json | 1.9.0 | Tree API only (no compiler plugin). |
| JUnit | 4.13.2 | JVM unit tests. |

## 3D renderer decision

The spec requires "a maintained Android GLB/glTF renderer based on Filament".

- **Chosen for Phase 0: Filament's own gltfio + `ModelViewer`** (Google, actively maintained).
  It is the lowest layer, has a small and long-stable API (`loadModelGlb`, `animator.applyAnimation`,
  `render`), and gives full control over the render loop and clip timing (needed for slow-motion and
  phase-synchronised demos).
- **Evaluated: SceneView** (Compose-native wrapper over Filament, stable on Android, actively
  released in 2026; v4.x pins Filament 1.71.x). Its Compose API changed substantially between major
  versions, which is a risk without a local compiler. Re-evaluate in Phase 2 if lesson screens need
  its higher-level scene graph (environment lighting, gestures). Switching is contained to
  `core/render3d`.

## Pose model handling

- `app/build.gradle.kts` task `downloadPoseModel` runs before every build and is up-to-date once the
  file exists.
- Offline builds still succeed; the camera spike then shows "Pose model unavailable" (no fake tracking).
- CI passes `-Pmotionforge.requirePoseModel=true`, so a missing model fails CI.
- Model is stored uncompressed in the APK (`noCompress "task"`); CI verifies this.

## Upgrade path (do in a dedicated PR, never mixed with features)

1. CameraX 1.4.2 → 1.6.x (check the 1.6.0 `ListenableFuture` compile issue is fixed in the chosen patch).
2. Compose BOM / lifecycle / navigation to current stable.
3. AGP 8.11 → 9.x with the Upgrade Assistant (removes `org.jetbrains.kotlin.android`).
4. Filament / MediaPipe patch updates after on-device regression of the spikes.

## androidx.core:core-splashscreen 1.2.0 (2026-11-21)
Launch screen with the MOTIONFORGE mark. 1.2.0 is the current stable release on the AndroidX Core release page.
Gives the Android 12+ splash API with an emulated version on Android 8-11 (minSdk 26).

## Screenshot tests: Robolectric 4.16 + Compose ui-test (2026-11-22)
`ScreenshotTest` renders the main screens on the JVM (Robolectric native graphics) so the design can be reviewed without
a device; CI runs it in its own step (MF_SCREENSHOTS=1) and pushes the PNGs to the `ci-screenshots` branch. Robolectric
4.16 is the current release and supports SDK 36; tests run on SDK 35 with JDK 17. Roborazzi was not used: its current
release is built with Kotlin 2.3, newer than this project's Kotlin 2.2. `ui-test-junit4` / `ui-test-manifest` come from
the Compose BOM.
## Font: Barlow family (OFL; replaced Archivo and Manrope 2026-11-22) (variable, OFL) replaces Big Shoulders Display + Schibsted Grotesk (2026-11-22)

## androidx.health.connect:connect-client 1.1.0 (2026-11-28)
Optional Health Connect export (Profile, off by default): each saved session is written as one `ExerciseSessionRecord`
(type, start/end, title) with `Metadata.activelyRecorded(clientRecordId, Device(TYPE_PHONE))`, so retries never
duplicate. 1.1.0 is the current stable release on the AndroidX Health Connect release page (the 1.2 line is alpha);
it needs minSdk 26 (this app's minimum). Write only (`android.permission.health.WRITE_EXERCISE`); nothing is read.
The privacy-note activity (`HealthPermissionsActivity`) answers `ACTION_SHOW_PERMISSIONS_RATIONALE` and, on Android 14+,
`VIEW_PERMISSION_USAGE` / `HEALTH_PERMISSIONS`. **Release:** Google Play requires the Health Connect permissions
declaration in the Play Console and a privacy policy that states this export before the build can be published.
