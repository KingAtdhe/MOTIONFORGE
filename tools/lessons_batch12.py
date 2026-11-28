"""Batch 12 lessons (2026-11-28): intermediate moves. Appends them to both copies of the catalogue if they are not
there yet. Run from the repo root. Guided (timer only) until a camera check is validated on rendered videos."""
import json

GUIDED = "The camera does not assess this move yet. Follow the demonstration; the timer guides you. {frame}"
IMPACT = ("This is a jumping move: land softly on the balls of the feet with soft knees. Keep a pace you could still "
          "talk at, and stop if you feel dizzy, short of breath, unwell, or pain in the joints. Swap for the low-impact "
          "version whenever you need to.")


def m(mistake, adjustment):
    return {"mistake": mistake, "adjustment": adjustment}


NEW = [
    {"id": "jump_squat", "name": "Jump Squat", "category": "fitness", "level": "intermediate", "durationSeconds": 30,
     "recommendedView": "front", "analysisMode": "guided_not_scored", "demoAnimation": "jump_squat",
     "purpose": "Build leg power with a squat that ends in a small, soft jump.",
     "space": "About 2 × 2 m of clear, non-slip floor.", "equipment": ["Supportive footwear (recommended)"],
     "safety": "Master the bodyweight squat first. " + IMPACT,
     "instructions": ["Stand with the feet about shoulder-width apart.",
                      "Squat down with the arms reaching forward.",
                      "Drive up through the whole foot and jump a little off the floor.",
                      "Land softly on the balls of the feet, sink into a small squat, then stand."],
     "commonCues": ["Land softly.", "Knees in line with the toes.", "Small jumps first."],
     "commonMistakes": [m("Landing on straight legs", "Land on the balls of the feet and let the knees bend."),
                        m("Knees caving in on landing", "Keep the knee in line with the toes."),
                        m("Jumping higher than you can land", "Make the jumps smaller and keep the body in one line.")],
     "limitations": GUIDED.format(frame="Face the phone with your whole body in view."),
     "reviewStatus": "draft_pending_coach_review"},
    {"id": "close_grip_push_up", "name": "Close-Grip Push-up", "category": "fitness", "level": "intermediate",
     "durationSeconds": 40, "recommendedView": "side", "analysisMode": "guided_not_scored", "demoAnimation": "close_grip_pushup",
     "purpose": "Work the triceps and chest harder with the hands close and the elbows tucked.",
     "space": "Floor space for your full body length. A sturdy wall or table works for the easier variation.",
     "equipment": ["Exercise mat (optional)"],
     "safety": "Master the push-up first. Stop if you feel pain in your wrists, elbows or shoulders.",
     "instructions": ["Start in a high plank with the hands under the shoulders.",
                      "Lower the chest with the elbows tucked close to the ribs, pointing back.",
                      "Keep one straight line from head to heels.",
                      "Press back up to the top."],
     "commonCues": ["Elbows back, close to the ribs.", "One straight line from head to heels.", "Lower slowly."],
     "commonMistakes": [m("Elbows flaring out to the sides", "Turn the elbows back toward the feet as you lower."),
                        m("Hips sagging or piking", "Try an easier incline variation with hands on a wall or sturdy table, or lower your knees to the floor."),
                        m("Dropping too fast", "Lower slowly and only as far as feels comfortable.")],
     "limitations": GUIDED.format(frame="Put the phone at floor level, side-on, with your whole body in view."),
     "reviewStatus": "draft_pending_coach_review"},
]

if __name__ == "__main__":
    for path in ("data/exercises.json", "app/src/main/assets/exercise_data/exercises.json"):
        raw = open(path, encoding="utf-8").read()
        data = json.loads(raw)
        have = {e["id"] for e in data}
        add = [e for e in NEW if e["id"] not in have]
        data.extend(add)
        open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
        print(path, "+", len(add), "->", len(data))
