"""Batch 8 lessons (2026-11-26): cool-down stretches. Appends them to both copies of the catalogue (data/exercises.json
and the app asset) if they are not there yet. Run from the repo root. Each has a hold check (HoldCheck) checked on
rendered videos of both coaches."""
import json

STAND = "About 2 × 2 m of clear, stable, non-slip floor."
SAFE = "Stretch gently to a mild pull, never into pain, and breathe slowly. Stop if you feel sharp pain, tingling or dizziness."


def m(mistake, adjustment):
    return {"mistake": mistake, "adjustment": adjustment}


def L(id_, name, secs, view, clip, purpose, space, equip, safety, steps, cues, mistakes, lim):
    return {"id": id_, "name": name, "category": "fitness", "level": "beginner", "durationSeconds": secs,
            "recommendedView": view, "analysisMode": "limited_rule_based", "demoAnimation": clip, "purpose": purpose,
            "space": space, "equipment": equip, "safety": safety, "instructions": steps, "commonCues": cues,
            "commonMistakes": mistakes, "limitations": lim, "reviewStatus": "draft_pending_coach_review"}


H = ("The camera times your stretch only while you're in the position ({how}); it does not judge how far you stretch or "
     "how long you should hold. {frame} Experimental.")

NEW = [
    L("standing_quad_stretch", "Standing Quad Stretch", 60, "side", "quad_stretch",
      "Stretch the front of the thigh after training, while practising balance.", STAND, ["Chair or wall for balance (optional)"],
      SAFE + " Hold a chair or wall if your balance is unsteady.",
      ["Stand tall on one leg, a hand on a chair or wall if you need it.",
       "Bend the other knee and bring the heel up behind you toward your seat.",
       "Hold the top of the foot with the same-side hand, knees side by side.",
       "Hold for a few slow breaths, lower the foot, and switch sides."],
      ["Knees side by side.", "Stand tall.", "Gentle pull, no pain."],
      [m("Pulling the knee out to the side or forward", "Keep the bent knee next to the standing knee, pointing down."),
       m("Arching the lower back", "Tuck the hips under a little and stand tall."),
       m("Yanking the foot up", "Ease the heel up only until you feel a mild stretch.")],
      H.format(how="one foot held up behind you, standing tall", frame="Stand side-on to the phone with your whole body in view.")),
    L("cross_body_shoulder_stretch", "Cross-Body Shoulder Stretch", 50, "front", "shoulder_stretch",
      "Stretch the back of the shoulder after punching, pushing or pulling.", STAND, [],
      SAFE + " Keep the pressure light on the elbow.",
      ["Stand tall, shoulders relaxed down.",
       "Bring one arm straight across the front of your chest at shoulder height.",
       "Hook the other forearm just above the elbow and draw the arm in gently.",
       "Hold for a few slow breaths, release, and switch sides."],
      ["Shoulders down.", "Arm across at chest height.", "Press above the elbow, not on it."],
      [m("Shrugging the shoulder up", "Let the shoulder sink away from your ear."),
       m("Pressing on the elbow joint", "Place the forearm just above the elbow."),
       m("Turning the whole body", "Keep the chest facing forward.")],
      H.format(how="one arm held across the front of your chest", frame="Face the phone with your upper body and both arms in view.")),
    L("overhead_triceps_stretch", "Overhead Triceps Stretch", 50, "front", "triceps_stretch",
      "Stretch the back of the upper arm and the side of the shoulder.", STAND, [],
      SAFE + " Skip it if raising the arm overhead hurts your shoulder.",
      ["Stand tall and reach one arm up.",
       "Bend the elbow so the hand drops behind your head toward your upper back.",
       "Rest the other hand on the raised elbow and draw it back gently.",
       "Hold for a few slow breaths, release, and switch sides."],
      ["Elbow points up.", "Head stays tall.", "Gentle pressure."],
      [m("Pushing the head forward", "Keep the head tall and the elbow beside it."),
       m("Arching the lower back", "Keep the ribs down and the core lightly braced.")],
      H.format(how="one elbow raised above your head", frame="Face the phone with your upper body and both arms in view.")),
    L("chest_opener_stretch", "Chest Opener", 45, "front", "chest_opener",
      "Open the chest and the front of the shoulders after push-ups or boxing.", STAND, [],
      SAFE + " Keep the chin level; don't push the head back.",
      ["Stand tall with the feet hip-width apart.",
       "Bring the hands together behind your lower back.",
       "Draw the shoulders back and down and let the chest lift a little.",
       "Hold for a few slow breaths, then release."],
      ["Shoulders back and down.", "Chest lifts.", "Chin level."],
      [m("Leaning back from the lower back", "Lift the chest instead and keep the ribs down."),
       m("Shrugging the shoulders up", "Let them sink away from the ears.")],
      H.format(how="standing tall with both hands together behind you", frame="Face the phone with your whole body in view.")),
    L("kneeling_hip_flexor_stretch", "Kneeling Hip Flexor Stretch", 60, "side", "hip_flexor_stretch",
      "Stretch the front of the hip, which gets tight from sitting and from lunges and squats.",
      "A mat-sized area of clear floor.", ["Exercise mat or folded towel under the knee (recommended)"],
      SAFE + " Pad the back knee; skip it if kneeling hurts.",
      ["Step one foot back and lower gently onto the back knee, on a mat or towel.",
       "Front knee above the ankle, chest tall, hands on the front thigh.",
       "Tuck the hips under a little and press them gently forward until you feel the front of the back hip stretch.",
       "Hold for a few slow breaths, come up, and switch sides."],
      ["Hips tuck under.", "Chest tall.", "Small forward press."],
      [m("Arching the lower back to go further", "Tuck the hips under; a small press is enough."),
       m("Front knee far past the toes", "Move the front foot a little further forward.")],
      H.format(how="kneeling on one knee with the chest tall",
               frame="Turn the phone sideways and put it at floor level, side-on, with your whole body in view.")),
]

for path in ("data/exercises.json", "app/src/main/assets/exercise_data/exercises.json"):
    raw = open(path).read()
    d = json.loads(raw)
    L_ = d if isinstance(d, list) else d["exercises"]
    have = {e["id"] for e in L_}
    L_ += [e for e in NEW if e["id"] not in have]
    open(path, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
print("lessons:", len(L_))
