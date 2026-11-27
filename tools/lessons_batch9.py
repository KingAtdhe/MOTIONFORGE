"""Batch 9 lessons (2026-11-27): mobility. Appends them to both copies of the catalogue (data/exercises.json and the
app asset) if they are not there yet. Run from the repo root. Guided: no camera check yet (none has been validated on
rendered videos for these), so the timer guides them."""
import json

STAND = "About 2 × 2 m of clear, stable, non-slip floor."
SAFE = "Move gently within a comfortable range, never into pain, and breathe slowly. Stop if you feel sharp pain, tingling or dizziness."
GUIDED = "The camera does not assess this move yet. Follow the demonstration; the timer guides you. {frame}"


def m(mistake, adjustment):
    return {"mistake": mistake, "adjustment": adjustment}


def L(id_, name, secs, view, clip, purpose, space, equip, safety, steps, cues, mistakes, frame):
    return {"id": id_, "name": name, "category": "fitness", "level": "beginner", "durationSeconds": secs,
            "recommendedView": view, "analysisMode": "guided_not_scored", "demoAnimation": clip, "purpose": purpose,
            "space": space, "equipment": equip, "safety": safety, "instructions": steps, "commonCues": cues,
            "commonMistakes": mistakes, "limitations": GUIDED.format(frame=frame), "reviewStatus": "draft_pending_coach_review"}


NEW = [
    L("leg_swings", "Leg Swings", 45, "side", "leg_swing",
      "Loosen the hips before training with an easy, controlled swing.", STAND, ["Wall or chair for balance (optional)"],
      SAFE + " Hold a wall or chair if your balance is unsteady.",
      ["Stand tall on one leg, a hand on a wall or chair if you need it.",
       "Swing the other leg forward and back from the hip, knee soft.",
       "Start small and let the swing grow a little, staying in control.",
       "Do about ten swings, then switch legs."],
      ["Stand tall.", "Swing from the hip.", "Smooth, not kicked."],
      [m("Kicking the leg up hard", "Let it swing like a pendulum; control the top of each swing."),
       m("Leaning back as the leg comes forward", "Keep the chest tall over the standing foot."),
       m("Arching the back as the leg goes back", "Keep the back swing small and the ribs down.")],
      "Stand side-on to the phone if you want to watch yourself."),
    L("hip_circles", "Hip Circles", 40, "front", "hip_circles",
      "Warm up the hips and lower back with slow circles.", STAND, [],
      SAFE,
      ["Stand with the feet a little wider than the hips, hands on the hips, knees soft.",
       "Draw slow circles with the hips, keeping the head over the feet.",
       "Do a few circles one way, then the other way."],
      ["Slow circles.", "Head stays still.", "Knees soft."],
      [m("Swinging the shoulders around", "Keep the upper body quiet; the hips draw the circle."),
       m("Rushing", "Take two or three seconds for each circle.")],
      "Face the phone with your whole body in view."),
    L("standing_hamstring_stretch", "Standing Hamstring Stretch", 60, "side", "hamstring_stretch",
      "Stretch the back of the thigh after leg work or running.", STAND, [],
      SAFE + " Keep the back flat; the stretch should be in the back of the thigh, not the lower back.",
      ["Step one heel forward, toes up, front leg long.",
       "Bend the back knee and sit the hips back.",
       "Tip forward from the hips with a flat back, hands resting on the front thigh.",
       "Hold for a few slow breaths, step back in, and switch sides."],
      ["Hips back.", "Flat back.", "Toes up."],
      [m("Rounding the back to reach lower", "Keep the back flat; tip only as far as the hips allow."),
       m("Locking the front knee hard", "Keep a small softness in the front knee."),
       m("Pressing on the knee", "Rest the hands on the thigh above the knee.")],
      "Stand side-on to the phone with your whole body in view."),
    L("squat_hold", "Deep Squat Hold", 45, "front", "squat_hold",
      "Open the hips and ankles by resting in a deep squat.", STAND, ["Small plate or book under the heels (optional)"],
      SAFE + " Go only as low as your knees and hips are comfortable; hold a support if you need it.",
      ["Feet wider than the hips, toes turned out a little.",
       "Sit down between your heels as low as is comfortable, chest up.",
       "Bring the palms together and let the elbows gently press the knees out.",
       "Breathe there, then stand up slowly."],
      ["Heels down.", "Chest up.", "Knees over the toes."],
      [m("Heels lifting", "Widen the stance a little or put a thin book under the heels."),
       m("Knees falling in", "Let the elbows guide the knees out over the toes."),
       m("Dropping down fast", "Lower slowly and stop where it's comfortable.")],
      "Face the phone with your whole body in view."),
    L("standing_calf_stretch", "Standing Calf Stretch", 50, "side", "calf_stretch",
      "Stretch the calves after walking, running, skipping or boxing footwork.", STAND, ["Wall for support (optional)"],
      SAFE + " Keep the back heel down without forcing it.",
      ["Step one foot back, toes pointing forward.",
       "Press the back heel down and keep that leg long.",
       "Bend the front knee and lean forward in one line from the back heel to the head, hands on the front thigh.",
       "Hold for a few slow breaths, step in, and switch sides."],
      ["Back heel down.", "Back leg long.", "One line, heel to head."],
      [m("Back heel lifting", "Shorten the step until the heel stays down."),
       m("Back toes turned out", "Point the back foot straight forward."),
       m("Bending at the waist", "Lean the whole body in one line instead.")],
      "Stand side-on to the phone with your whole body in view."),
]

for path in ("data/exercises.json", "app/src/main/assets/exercise_data/exercises.json"):
    raw = open(path).read()
    d = json.loads(raw)
    L_ = d if isinstance(d, list) else d["exercises"]
    have = {e["id"] for e in L_}
    L_ += [e for e in NEW if e["id"] not in have]
    open(path, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
print("lessons:", len(L_))
