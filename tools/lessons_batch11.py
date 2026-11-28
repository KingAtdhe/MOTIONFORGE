"""Batch 11 lessons (2026-11-28): core & abs. Appends them to both copies of the catalogue (data/exercises.json and
the app asset) if they are not there yet. Run from the repo root. Guided (timer only) until a camera check is validated
on rendered videos of both coaches; this script never rewrites a lesson that is already there."""
import json

MAT = "A mat-sized area of clear floor."
MATQ = ["Exercise mat (optional)"]
GUIDED = "The camera does not assess this move yet. Follow the demonstration; the timer guides you. {frame}"
FLOOR_SIDE = "Put the phone at floor level, side-on, with your whole body in view."
FLOOR_FRONT = "Put the phone at floor level in front of you, with your whole body in view."


def m(mistake, adjustment):
    return {"mistake": mistake, "adjustment": adjustment}


def L(id_, name, secs, view, clip, purpose, safety, steps, cues, mistakes, frame):
    return {"id": id_, "name": name, "category": "fitness", "level": "beginner", "durationSeconds": secs,
            "recommendedView": view, "analysisMode": "guided_not_scored", "demoAnimation": clip, "purpose": purpose,
            "space": MAT, "equipment": MATQ, "safety": safety, "instructions": steps, "commonCues": cues,
            "commonMistakes": mistakes, "limitations": GUIDED.format(frame=frame), "reviewStatus": "draft_pending_coach_review"}


BACK_NECK = "Stop if you feel pain in your neck or back."

NEW = [
    L("hollow_hold", "Hollow Hold (Tuck)", 25, "side", "hollow_hold",
      "Build deep core strength by holding a curled, braced position on your back.",
      "Keep the lower back pressed into the floor; if it lifts, bring the knees closer. " + BACK_NECK,
      ["Lie on your back with the knees bent and the feet on the floor.",
       "Lift the legs into tabletop, knees over the hips.",
       "Press the lower back into the floor and lift the head and shoulders.",
       "Reach the arms long toward the knees and hold, breathing steadily."],
      ["Lower back stays down.", "Ribs toward the hips.", "Keep breathing."],
      [m("Lower back arching off the floor", "Bring the knees closer to the chest until the back stays down."),
       m("Straining the neck", "Look at the ceiling, chin slightly tucked."),
       m("Holding the breath", "Breathe slowly in and out through the hold.")],
      FLOOR_SIDE),
    L("bent_knee_leg_raise", "Bent-Knee Leg Raise", 40, "side", "leg_raise",
      "Strengthen the lower abdominals by lifting and lowering the legs with control.",
      "Lower only as far as the lower back stays down, and never let the legs drop. " + BACK_NECK,
      ["Lie on your back, arms on the floor beside you, knees bent.",
       "Lift the feet just off the floor.",
       "Raise the knees up over the hips, keeping the knees bent.",
       "Lower slowly until the feet hover just above the floor, then lift again."],
      ["Lower back stays down.", "Slow on the way down.", "Feet never touch."],
      [m("Swinging the legs", "Make the movement smaller and slower."),
       m("Lower back arching off the floor", "Lower the legs less far."),
       m("Pushing hard into the floor with the arms", "Let the stomach do the work.")],
      FLOOR_SIDE),
    L("bicycle_crunch", "Bicycle Crunch", 40, "side", "bicycle_crunch",
      "Work the abdominals and obliques with a slow, twisting crunch.",
      "Keep the hands light at the head and never pull on the neck. Move slowly. " + BACK_NECK,
      ["Lie on your back with the fingertips at your temples, elbows wide.",
       "Lift the head and shoulders and bring the knees up.",
       "Bring one knee in as the other leg lengthens low, and turn the opposite shoulder toward the bent knee.",
       "Switch sides slowly, keeping the shoulders lifted."],
      ["Shoulder to knee.", "Elbows wide.", "Slow down."],
      [m("Pulling on the neck", "Keep the fingertips light; the turn comes from the ribs."),
       m("Pedalling fast", "Slow down and pause on each side."),
       m("Lower back arching as the leg lengthens", "Keep the long leg higher.")],
      FLOOR_SIDE),
    L("plank_leg_lift", "Plank Leg Lift", 40, "side", "plank_leg_lift",
      "Challenge core stability and the glutes by lifting one leg from a forearm plank.",
      "Master the forearm plank first. Lift only as high as the hips stay level. Stop if you feel pain in your back or shoulders.",
      ["Start in a forearm plank, elbows under the shoulders.",
       "Squeeze the glute and lift one straight leg a hand's width off the floor.",
       "Keep the hips level and square to the floor.",
       "Lower it with control, then lift the other leg."],
      ["Hips stay level.", "Small lift.", "One straight line from head to heels."],
      [m("Hips twisting as the leg lifts", "Lift the leg lower."),
       m("Hips sagging toward the floor", "Squeeze your glutes gently, or rest on your knees and hold a shorter time."),
       m("Holding the breath", "Breathe slowly in and out through the hold.")],
      FLOOR_SIDE),
    L("glute_bridge_march", "Glute Bridge March", 40, "side", "glute_bridge_march",
      "Train the glutes and core to keep the hips level while one foot lifts.",
      "Master the two-leg glute bridge first. " + BACK_NECK,
      ["Lie on your back with the knees bent and the feet flat.",
       "Lift the hips into a bridge, shoulders, hips and knees in line.",
       "Lift one foot a little off the floor, keeping the knee bent, and set it down.",
       "Then lift the other foot, keeping the hips high and level."],
      ["Hips level.", "Press through the heel.", "Ribs down."],
      [m("One hip dropping", "Lift less high and keep the hips level."),
       m("Arching the lower back at the top", "Lift a little lower and think of keeping your ribs down."),
       m("Hips sinking as the foot lifts", "Make the foot lift smaller.")],
      FLOOR_SIDE),
    L("side_plank_knees", "Side Plank (Knees)", 25, "front", "side_plank_knees",
      "Strengthen the side of the core in an easier side plank from the knees.",
      "Keep the elbow under the shoulder. Stop if you feel pain in your shoulder, hips or back.",
      ["Lie on your side, propped on the forearm, elbow under the shoulder.",
       "Bend the knees so the feet are behind you.",
       "Lift the hips until the head, hips and knees line up.",
       "Rest the top hand on the hip and hold, breathing steadily. Then switch sides."],
      ["Elbow under shoulder.", "Hips up.", "Keep breathing."],
      [m("Hips sagging toward the floor", "Lift the hips into one line, or hold a shorter time."),
       m("Shoulder sinking toward the ear", "Push the floor away with the forearm."),
       m("Holding the breath", "Breathe slowly in and out through the hold.")],
      FLOOR_FRONT),
    L("side_plank", "Side Plank", 25, "front", "side_plank",
      "Strengthen the side of the core holding one straight line on the forearm.",
      "Try the side plank from the knees first. Keep the elbow under the shoulder. Stop if you feel pain in your shoulder, hips or back.",
      ["Lie on your side, propped on the forearm, elbow under the shoulder.",
       "Straighten the legs and stack the feet.",
       "Lift the hips until the body forms one straight line from head to heels.",
       "Rest the top hand on the hip and hold, breathing steadily. Then switch sides."],
      ["Elbow under shoulder.", "One straight line from head to heels.", "Keep breathing."],
      [m("Hips sagging toward the floor", "Lift the hips into one line, or hold a shorter time."),
       m("Shoulder sinking toward the ear", "Push the floor away with the forearm."),
       m("Rolling forward or back", "Stack the hips and shoulders, chest facing forward.")],
      FLOOR_FRONT),
]

if __name__ == "__main__":
    for path in ("data/exercises.json", "app/src/main/assets/exercise_data/exercises.json"):
        data = json.load(open(path, encoding="utf-8"))
        have = {e["id"] for e in data}
        add = [e for e in NEW if e["id"] not in have]
        data.extend(add)
        json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(path, "a").write("\n")
        print(path, "+", len(add), "->", len(data))
