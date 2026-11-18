# MOTIONFORGE — Implementation Plan

Build in vertical slices. Do not attempt every feature at once.

## Phase 0 — Feasibility and project foundation

Deliver:
- Android Studio project.
- Kotlin/Compose baseline.
- Gradle version catalog.
- Navigation skeleton.
- Unit test setup.
- CameraX compatibility spike.
- MediaPipe Pose Landmarker compatibility spike.
- GLB renderer compatibility spike.
- A documented dependency/version decision.

Acceptance:
- App builds on a clean checkout.
- One Android emulator/device can launch it.
- Camera preview can be opened in a test screen.
- Pose sample can process a frame.
- One simple GLB can load and play an animation.
- Risks and unresolved library compatibility are documented.

Do not proceed to polished UI until these technical spikes are proven.

## Phase 1 — Product shell and offline catalogue

Deliver:
- Theme and reusable components.
- Onboarding.
- Adult age confirmation.
- Safety notice.
- Home screen.
- Fitness/Fighting categories.
- Lesson catalogue and detail screen.
- Local JSON-backed content.
- Guest mode.

Acceptance:
- User can navigate the core app without login.
- Every visible control works.
- Empty/error/loading states are implemented.

## Phase 2 — 3D coach

Deliver:
- GLB asset pipeline.
- Trainer viewer.
- Animation selection.
- Pause/replay/slow playback.
- Camera angle controls where supported.
- Text instructions and common mistakes.
- Static fallback.

Acceptance:
- All bundled assets load on tested Android devices.
- No app crash if a model fails to load.
- Animation controls behave consistently.

## Phase 3 — Camera and pose tracking

Deliver:
- Permission rationale.
- CameraX preview.
- Image analysis pipeline.
- MediaPipe integration.
- Landmark normalization.
- Confidence checks.
- Tracking status UI.
- Landmark overlay.
- Camera setup guide.

Acceptance:
- Camera opens and closes with lifecycle.
- ImageProxy is always closed.
- No frame processing on main thread.
- Permission denial is handled.
- Unsupported view does not show fake feedback.
- No frames are saved or uploaded.

## Phase 4 — Movement feedback MVP

Deliver:
- Squat evaluator first.
- Boxing stance evaluator second.
- Jab/guard phase cues only after review.
- Repetition state machine where appropriate.
- Unit tests with synthetic landmarks.
- Confidence/occlusion handling.

Acceptance:
- Every cue maps to a documented rule.
- Low-confidence frames suppress feedback.
- Repetition counter avoids obvious double counts.
- Coach review and device test results are documented.
- User can disable live feedback and use demo-only mode.

## Phase 5 — Session and progress

Deliver:
- Session timer.
- Exercise sequence.
- Rest intervals.
- Pause/stop.
- Session summary.
- Room persistence.
- History and weekly trends.

Acceptance:
- Sessions survive app process restart where appropriate.
- Local progress works offline.
- Invalid/incomplete sessions are handled correctly.

## Phase 6 — Optional account and cloud sync

Deliver:
- Supabase Auth.
- User-owned profile.
- Session sync.
- Row Level Security policies.
- Account deletion flow.

Acceptance:
- Guest mode still works.
- Users only access their own records.
- No camera media is uploaded.
- Secrets remain server-side.

## Phase 7 — Beta hardening

Deliver:
- Device compatibility testing.
- Performance and thermal checks.
- Accessibility review.
- Privacy review.
- Crash reporting with privacy-safe configuration.
- Store listing draft.
- Beta feedback process.

Acceptance:
- No known critical security/privacy defects.
- Known tracking limitations are disclosed.
- App is tested on multiple real Android devices.
- No unsupported claims in marketing.

## Phase 8 — Monetization (after validation)

Only after users complete sessions and show retention:
- Premium entitlement model.
- Play Billing integration.
- Restore purchases.
- Subscription management.
- Server-side receipt/entitlement verification.
- Clear cancellation and pricing disclosures.

Do not implement payment before the core product is useful.

## Build budget

A prototype may be possible with:
- Free development tools.
- Free GitHub repository.
- Free Supabase/hosting tiers within limits.
- Open-source pose estimation.
- Self-created Blender assets.

Potential costs:
- Google Play developer registration fee.
- Domain.
- API usage if optional cloud AI is introduced.
- Paid asset licenses.
- Hosting/database usage beyond free tiers.
- External coach review and testing.

The €100 target is a prototype constraint, not a guarantee of a production launch under €100.
