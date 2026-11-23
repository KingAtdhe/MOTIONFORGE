# Batch 4 — work in progress (handoff)

Done (on this branch, not yet CI-verified):
- Clips in tools/blender/authored_clips.py: knee_crunch, db_reverse_fly, db_overhead_triceps (bottom fixed: elbows up,
  forearms behind head), boxing_jab_jab_cross. Both coaches rebuilt; QC sheets, close-ups and clip_audit clean
  (no foot slide, floor contact steady).
- Lessons (app + data/exercises.json in sync, 50 total): standing_knee_crunch, dumbbell_reverse_fly,
  dumbbell_overhead_triceps_extension, boxing_jab_jab_cross; high_knee_march now counted (limited_rule_based).
- Counters: KneeLiftRepCounter (KNEE_LIFT: knee crunch + high-knee march; minRep 150, knee visibility 0.4),
  OverheadDropRepCounter (OVERHEAD: triceps extension, direction −1, travel 0.30); reverse fly → ROW;
  1-1-2 → PUNCH.
- Tests updated: catalog count 50, clip lists, equipment set. Study SHOTS added in render_thumbs.py.

Verified on rendered videos (mirror2.py): knee crunch 8/8 at front, side, 3/4; high-knee march 8/8 side + front dim.

Still to do:
1. Finish queue8 renders (revfly, ohtri, jjc, southpaw, negative idle) — `runq8.sh` (batch.sh skips finished .lm).
   Check with `check8.py`. 1-1-2 may count 2 per combo (jab return between jabs) — decide per-combo vs per-punch.
2. Copy passing .lm to app/src/test/resources/pose_fixtures (gzip) + expected.txt lines.
3. Render motion studies for both coaches (render_studies.py + compose_studies.py) for the 4 new lessons.
4. BUILD_LOG entry, merge to main, CI, report APK link.
