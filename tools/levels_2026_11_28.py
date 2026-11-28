"""Harder levels (2026-11-28): marks the lessons that ask more than a beginner can safely start with as
"intermediate", in both copies of the catalogue. Run from the repo root; idempotent."""
import json

INTERMEDIATE = {
    # fitness: full push-ups, single-leg and loaded hinges, dips, swings, unstable planks, jumping moves
    "push_up", "single_leg_rdl", "single_leg_glute_bridge", "bench_dip", "kettlebell_swing", "plank_shoulder_taps",
    "side_plank", "plank_leg_lift", "skater_hop", "plank_jack", "mountain_climber",
    # fighting fundamentals: three-punch combinations and defend-then-counter drills
    "boxing_roll_hook", "boxing_pull_counter", "boxing_slip_cross", "boxing_jab_slip", "boxing_block_cross",
    "boxing_cross_hook_cross", "boxing_one_two_uppercut", "boxing_uppercut_hook", "boxing_hook_cross",
    "boxing_jab_body_cross", "boxing_body_head_jab",
}

if __name__ == "__main__":
    for path in ("data/exercises.json", "app/src/main/assets/exercise_data/exercises.json"):
        raw = open(path, encoding="utf-8").read()
        data = json.loads(raw)
        ids = {e["id"] for e in data}
        missing = INTERMEDIATE - ids
        assert not missing, missing
        n = 0
        for e in data:
            want = "intermediate" if e["id"] in INTERMEDIATE else e["level"]
            if e["level"] != want:
                e["level"] = want
                n += 1
        open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
        print(path, "changed", n, "| intermediate", sum(e["level"] == "intermediate" for e in data), "of", len(data))
