# Movement Analysis, Validation & Safety

## 1. Scope

MOTIONFORGE provides educational movement cues for a limited set of beginner exercises and non-contact fighting fundamentals. It does not provide medical advice or certify technique.

## 2. Camera setup states

The UI must distinguish:
- CAMERA_PERMISSION_REQUIRED
- CAMERA_PERMISSION_DENIED
- CAMERA_INITIALIZING
- MOVE_INTO_VIEW
- ADJUST_CAMERA
- CALIBRATING
- TRACKING
- LOW_CONFIDENCE
- OCCLUDED
- UNSUPPORTED_VIEW
- PAUSED
- CAMERA_ERROR

Never present movement feedback while the state is not TRACKING.

## 3. Feedback language

Prefer:
- "Your knees may be moving inward. Try a comfortable stance and check your alignment."
- "Your upper body is partly out of view. Adjust the camera."
- "I can't assess this movement from the current angle."
- "Try a slower repetition so you can focus on control."

Avoid:
- "Your form is dangerous."
- "You will injure yourself."
- "Your technique is perfect."
- "This prevents injury."
- "You are medically cleared."

## 4. Example rule architecture

Each movement evaluator should implement:
- Required landmarks.
- Recommended camera view.
- Confidence thresholds.
- Calibration requirements.
- Movement phases.
- Measurable cues.
- Cooldown/debounce.
- Unsupported conditions.
- Unit tests using synthetic landmark fixtures.

Do not implement numerical thresholds as universal biomechanical truths. Treat initial thresholds as hypotheses to be calibrated and reviewed by qualified coaches.

## 5. Initial movement support matrix

| Movement | MVP camera view | MVP analysis |
|---|---|---|
| Squat | Front or side, selected explicitly | Basic phase/repetition and limited alignment cue |
| Push-up | Side | Body visibility and repetition phase only after validation |
| Hip hinge | Side | Demo/guided only initially |
| Boxing stance | Front/diagonal | Stance setup cues, not a quality score |
| Jab | Front/diagonal | Movement-phase cue only |
| Cross | Front/diagonal | Movement-phase cue only |
| Guard return | Front/diagonal | Return-to-guard cue |
| Footwork | Full body | Guided timing, no automatic form score |

### Added lessons (2026-11-25)

Every lesson except the bodyweight hip hinge, the standing warm-up and the footwork drills now has a live camera
check, each checked on rendered videos of both coaches (`RenderedVideoRepTest`, `tools/pose_tests`):

- **Counted** (`CountedMove` + `MoreMoves`): one plain measurement per lesson, read only while the body is in the
  lesson's position (lying, on all fours, standing...): e.g. knee angle for dead bug / bird dog / butt kicks, hip
  angle for climbers / reverse crunch / kettlebell swing, heel height over the toes for calf raises, torso pitch for
  hinges, hand position for twists and heel taps, hip travel for skater steps. A rep needs the full excursion and the
  return; a tracking gap drops it. No form judgement beyond the cues listed in the code.
- **Held positions** (`HoldCheck` / `HoldMonitor`: planks, bear hold, wall sit, single-leg balance, child's pose,
  arm circles): the timer runs only while the position is seen for most of the last second; planks may suggest
  lifting / lowering the hips into one line (side-on), the wall sit sliding a little lower. Never how long to hold.
- **Guard check** (`BoxingDrill.GUARD_CHECKED`, the stance rules): defence drills, combos, punches — "hands up by
  your face", feet width. No cue on any correct demo video.
- Views that cannot see the movement are named in the lesson's camera text (calf raise and dips side-on; shoulder
  taps, donkey kicks and fire hydrants from a front corner — side-on the far limb is hidden).

## 6. Fighting safety

- Only non-contact beginner fundamentals in MVP.
- No sparring instructions.
- No striking another person or object.
- No heavy bag power advice.
- No claims about punch power, impact, knockouts, or combat effectiveness.
- Recommend clear floor space and appropriate footwear.
- Tell users to stop if they feel pain, dizziness, or unusual discomfort.
- Encourage instruction from a qualified coach for martial arts technique.
- Never encourage training through pain.

## 7. General fitness safety

- Warm-up prompts.
- User-controlled pace.
- Clear pause/stop.
- Rest prompts.
- No forced progression.
- Do not prescribe rehabilitation.
- Do not personalize based on diagnoses.
- Adult-only MVP (18+).
- Users should consult qualified professionals when unsure whether an activity is appropriate for them.

## 8. Validation plan

Before enabling live feedback for a movement:
1. Have a qualified fitness or martial arts coach review the cue and demonstration.
2. Test different body shapes, clothing, lighting, camera heights, distances, and phone models.
3. Test occlusion and off-angle views.
4. Measure false-positive and missed-feedback rates.
5. Ensure unsupported views produce "unable to assess", not guessed feedback.
6. Keep feedback conservative.
7. Record test methodology and known limitations.

Do not claim validated accuracy without a documented study and representative test set.
