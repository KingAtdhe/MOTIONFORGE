"""Batch 10 lessons (2026-11-28): cardio & HIIT. Appends them to both copies of the catalogue (data/exercises.json and
the app asset) if they are not there yet. Run from the repo root. They start guided (timer only); a lesson gets a
camera count only once a check has been validated on rendered videos of both coaches (then its analysisMode and
limitations are changed in the catalogue itself; this script never rewrites a lesson that is already there)."""
import json

ROOM = "About 2 × 2 m of clear, non-slip floor with room to move your arms."
MAT = "A mat-sized area of clear floor."
FIGHT = "Clear space in front of you at least an arm's length plus a step. Nothing and nobody within reach."
SHOES = ["Supportive footwear (recommended)"]
MATQ = ["Exercise mat (optional)"]
IMPACT = ("This is a jumping move: land softly on the balls of the feet with soft knees. Keep a pace you could still "
          "talk at, and stop if you feel dizzy, short of breath, unwell, or pain in the joints. Swap for the low-impact "
          "version whenever you need to.")
GUIDED = "The camera does not assess this move yet. Follow the demonstration; the timer guides you. {frame}"


def m(mistake, adjustment):
    return {"mistake": mistake, "adjustment": adjustment}


def L(id_, name, cat, secs, view, clip, purpose, space, equip, safety, steps, cues, mistakes, frame):
    return {"id": id_, "name": name, "category": cat, "level": "beginner", "durationSeconds": secs,
            "recommendedView": view, "analysisMode": "guided_not_scored", "demoAnimation": clip, "purpose": purpose,
            "space": space, "equipment": equip, "safety": safety, "instructions": steps, "commonCues": cues,
            "commonMistakes": mistakes, "limitations": GUIDED.format(frame=frame), "reviewStatus": "draft_pending_coach_review"}


F, B = "fitness", "fighting_fundamentals"
FRONT = "Face the phone with your whole body in view."
SIDE = "Stand side-on to the phone with your whole body in view."

NEW = [
    L("jumping_jack", "Jumping Jack", F, 40, "front", "jumping_jack",
      "Raise the heart rate with a classic full-body jump.", ROOM, SHOES, IMPACT,
      ["Stand with your feet close together and arms by your sides.",
       "Jump the feet out wide as both arms sweep up overhead.",
       "Jump the feet back together as the arms come down.",
       "Keep a steady rhythm, landing softly each time."],
      ["Land softly.", "Arms long overhead.", "Steady rhythm."],
      [m("Landing flat-footed and stiff", "Land on the balls of the feet and let the knees bend."),
       m("Knees caving in on landing", "Keep the knee in line with the toes."),
       m("Arms only half-way up", "Reach all the way overhead, or slow down until you can.")],
      FRONT),
    L("high_knees", "High Knees", F, 30, "side", "high_knees",
      "A quick jog on the spot that drives the knees up and gets the heart pumping.", ROOM, SHOES, IMPACT,
      ["Stand tall with the feet hip-width apart.",
       "Jog on the spot, driving each knee up toward hip height.",
       "Stay on the balls of the feet and pump the arms with the legs.",
       "Keep the chest tall the whole time."],
      ["Knees up.", "Light feet.", "Pump the arms."],
      [m("Leaning back to lift the knee", "Keep the chest tall; lift only as high as you can upright."),
       m("Stamping the feet", "Bounce lightly on the balls of the feet."),
       m("Arms still", "Swing the arms in rhythm with the legs.")],
      SIDE),
    L("butt_kick_jog", "Butt Kicks", F, 30, "side", "butt_kick_jog",
      "A quick jog on the spot that flicks the heels up behind to warm the legs.", ROOM, SHOES, IMPACT,
      ["Stand tall with the feet hip-width apart.",
       "Jog on the spot, flicking each heel up behind toward your seat.",
       "Keep the thigh pointing down; only the heel lifts.",
       "Bounce lightly on the balls of the feet."],
      ["Heels up behind.", "Knees point down.", "Quick and light."],
      [m("Knees swinging forward", "Keep the thighs near vertical; only the lower leg moves."),
       m("Leaning forward", "Stay tall through the chest."),
       m("Heavy landings", "Land softly and quietly.")],
      SIDE),
    L("fast_feet", "Fast Feet", F, 25, "front", "fast_feet",
      "Quick, light steps in a low ready stance for speed and conditioning.", ROOM, SHOES,
      "Keep the steps small and light. Stop if you feel dizzy, short of breath or unwell, or pain in the joints.",
      ["Feet wider than the hips, knees bent, chest a little forward.",
       "Step quickly on the spot on the balls of the feet.",
       "Keep the steps small and the hips low.",
       "Keep the arms relaxed and ready in front of you."],
      ["Small, quick steps.", "Stay low.", "On the balls of the feet."],
      [m("Standing up tall as you speed up", "Keep the knees bent and the hips low."),
       m("Big, slow steps", "Keep the feet just off the floor and quick."),
       m("Holding the breath", "Breathe steadily throughout the movement.")],
      FRONT),
    L("skater_hop", "Skater Hop", F, 40, "front", "skater_hop",
      "A side-to-side bound for leg power and balance.", "About 3 × 2 m of clear, non-slip floor.", SHOES, IMPACT,
      ["Stand on one leg with the knee bent and the chest a little forward.",
       "Push off and bound sideways onto the other foot.",
       "Land softly on a bent knee, the free foot swinging behind you.",
       "Pause for balance, then bound back."],
      ["Soft landing.", "Knee over the toes.", "Swing the arms across."],
      [m("Landing on a straight leg", "Bend the knee as the foot lands to absorb the bound."),
       m("Knees falling inward", "Keep the knee in line with the toes."),
       m("Bounding too far too soon", "Start with small bounds and widen as your balance allows.")],
      FRONT),
    L("plank_jack", "Plank Jack", F, 30, "side", "plank_jack",
      "Raise the heart rate while holding a strong high plank.", MAT, MATQ,
      "Keep the hips level and the hands under the shoulders. Stop if you feel pain in the wrists, shoulders or back.",
      ["Start in a high plank, hands under the shoulders, feet together.",
       "Jump both feet out wide.",
       "Jump them back together.",
       "Keep the hips level and the core tight throughout."],
      ["Hips level.", "Shoulders over hands.", "Light feet."],
      [m("Hips bouncing up and down", "Make the jumps smaller and keep the body in one line."),
       m("Shoulders drifting behind the hands", "Keep the shoulders stacked over the wrists."),
       m("Sagging lower back", "Tighten the core and squeeze the glutes.")],
      "Put the phone at floor level, side-on, with your whole body in view."),
    L("mountain_climber", "Mountain Climber", F, 30, "side", "mountain_climber",
      "Drive the knees in quickly from a high plank for conditioning and core strength.", MAT, MATQ,
      "Keep the hips level and the hands under the shoulders. Slow down if the plank position changes, and stop if you "
      "feel pain in the wrists, shoulders or back.",
      ["Start in a high plank with your hands under your shoulders.",
       "Bring one knee toward your chest.",
       "Switch legs quickly, one knee in as the other goes back.",
       "Keep the hips level and the shoulders over the hands."],
      ["Shoulders over hands.", "Hips level.", "Quick knees."],
      [m("Hips piking up", "Make one straight line from head to heels."),
       m("Shoulders drifting back", "Keep the shoulders over the wrists."),
       m("Bouncing the hips", "Slow down until the hips stay still.")],
      "Put the phone at floor level, side-on, with your whole body in view."),
    L("boxing_speed_punches", "Speed Punches", B, 30, "front_or_diagonal", "boxing_speed_punches",
      "Quick, relaxed jab-cross pairs to build hand speed and conditioning.", FIGHT, [],
      "Practise in the air only, without contact. Keep the punches relaxed and never lock the elbows. Stop if you feel "
      "pain in the shoulders, elbows or wrists.",
      ["Start in your boxing stance, hands up.",
       "Throw a quick jab, then a quick cross.",
       "Bring each hand straight back to your face.",
       "Keep a steady, relaxed rhythm with a light bounce."],
      ["Quick out, quick back.", "Stay relaxed.", "Hands home."],
      [m("Dropping the hands between punches", "Bring each hand back to your face before the next one."),
       m("Locking the elbows", "Stop each punch just short of full extension."),
       m("Tensing up", "Breathe out on each punch and keep the shoulders loose.")],
      "Face the phone or stand at a slight angle, with your upper body in view."),
]

if __name__ == "__main__":
    for path in ("data/exercises.json", "app/src/main/assets/exercise_data/exercises.json"):
        raw = open(path).read()
        d = json.loads(raw)
        L_ = d if isinstance(d, list) else d["exercises"]
        have = {e["id"] for e in L_}
        L_ += [e for e in NEW if e["id"] not in have]
        open(path, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
    print("lessons:", len(L_))
