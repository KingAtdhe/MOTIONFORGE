# QA, Testing and Release Checklist

## 1. Functional testing

- Fresh install.
- Onboarding complete.
- Adult confirmation.
- Safety notice visible.
- Guest mode.
- Category navigation.
- Lesson list.
- Lesson detail.
- GLB load and fallback.
- Animation pause/replay/slow.
- Camera permission allow/deny.
- Camera preview lifecycle.
- App background/foreground.
- Phone rotation.
- Camera unavailable.
- Pose confidence low.
- User out of frame.
- Session pause/stop.
- Session summary.
- Local history.
- Settings and data reset.

## 2. Camera and pose tests

Test:
- Front camera and rear camera if supported.
- Different lighting.
- Bright backlight.
- Dark room.
- Loose clothing.
- Occluded joints.
- Partial body out of frame.
- Different camera distances.
- Different phone orientations.
- Low-end and mid-range Android devices.
- Thermal throttling.

Expected result when tracking quality is inadequate: show an understandable setup instruction or "unable to assess". Never guess.

## 3. Privacy tests

- Camera permission is requested only when required.
- No camera use in background.
- No frame/video files written to storage.
- No frame/video upload.
- No frame/image content in logs.
- Local data deletion works.
- Supabase RLS tests pass before cloud sync release.
- Secrets are absent from APK/source control.

## 4. Accessibility

- Adequate contrast.
- Screen-reader labels.
- Touch targets suitable for mobile.
- Do not rely on color alone for feedback.
- Text alternatives for demonstrations.
- Captions/text for audio cues.
- Reduced motion option for UI animations.

## 5. Release gates

Do not publish publicly until:
- Build is reproducible.
- Privacy policy accurately describes actual data handling.
- Camera permission rationale is clear.
- Store data-safety declarations match implementation.
- All training content has appropriate safety review.
- 3D assets have documented ownership/licenses.
- Unsupported technique claims are removed.
- Crash and performance testing is completed.
