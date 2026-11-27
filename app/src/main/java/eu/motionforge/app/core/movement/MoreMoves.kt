package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark

/**
 * Counters for the lessons added to live coaching on 2026-11-25. Each signal is a plain measurement on the pose,
 * normalised by the torso length or an angle, and only read while the body is in the lesson's position (lying,
 * on all fours, standing...), so the counter never counts something else. Thresholds were set on rendered videos of
 * both coaches (front / side / 3-4 views, tools/pose_tests) for coach review; every counter is a plain
 * [ExcursionRepCounter] or [TwoSidedRepCounter]: a rep needs the full excursion and the return, a tracking gap drops
 * it, and nothing is judged beyond the listed cues.
 */
object MoreMoves {
    /** Torso between [lo] and [hi] degrees from upright (90 = lying or on all fours). */
    private fun PoseReader.torsoIn(lo: Double, hi: Double) = torso?.tilt?.let { it in lo..hi } == true

    fun counterFor(move: CountedMove): RepCounter? = when (move) {
        // plank: the knee driving in closes the hip angle (shoulder–hip–knee) from ~165° to under ~110°
        CountedMove.CLIMBER -> SignalRepCounter(-1, travel = 45.0, minRepMs = 300) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> r.angle(s.shoulder, s.hip, s.knee, 0.3f) }.minOrNull()
        }
        // on the back: a leg reaching long opens the knee from ~98° (tabletop) to ~160°
        CountedMove.DEAD_BUG -> SignalRepCounter(+1, travel = 35.0, minRepMs = 500) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> r.angle(s.hip, s.knee, s.ankle, 0.3f) }.maxOrNull()
        }
        // all fours: the leg reaching back opens the knee from ~88° to ~160°
        CountedMove.BIRD_DOG -> SignalRepCounter(+1, travel = 40.0, minRepMs = 500) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> r.angle(s.hip, s.knee, s.ankle, 0.3f) }.maxOrNull()
        }
        // lying face down: the feet lift ~0.2 torso lengths above the hips
        CountedMove.SUPERMAN -> SignalRepCounter(+1, travel = 0.10, minRepMs = 500) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> r.above(s.ankle, s.hip) }.maxOrNull()
        }
        // all fours: the head drops with the rounded back (cat) and lifts with the arched back (cow), ~0.2 torso lengths
        CountedMove.CAT_COW -> SignalRepCounter(+1, travel = 0.12, minRepMs = 400) { r ->
            val t = r.torso
            if (t == null || !r.torsoIn(60.0, 120.0) || !r.seen(BodyLandmark.NOSE)) null else (t.sy - r.y(BodyLandmark.NOSE)) / t.len
        }
        // standing: the working leg swings away from vertical (hip→ankle), back for kickbacks, out for side raises
        CountedMove.LEG_SWING -> SignalRepCounter(+1, travel = 15.0, minRepMs = 500) { r ->
            if (!r.torsoIn(0.0, 35.0)) null
            else r.sides { s -> if (r.seenAt(0.4f, s.hip, s.ankle)) Math.toDegrees(kotlin.math.atan2(kotlin.math.abs(r.x(s.ankle) - r.x(s.hip)), r.y(s.ankle) - r.y(s.hip))) else null }.maxOrNull()
        }
        // standing side-on, one leg swinging like a pendulum: the swinging leg's hip→ankle line leaves vertical, ~25–30°
        // forward and ~20° back on the rendered videos; each swing forward and each swing back is one (they pass the
        // vertical between them). Half a swing takes ~0.55 s at the demo tempo.
        CountedMove.LEG_PENDULUM -> PendulumRepCounter(travel = 25.0, side = 8.0) { r ->
            if (!r.torsoIn(0.0, 25.0)) null
            else {
                val legs = r.sides { s -> if (r.seenAt(0.4f, s.hip, s.ankle)) Math.toDegrees(kotlin.math.atan2(r.x(s.ankle) - r.x(s.hip), r.y(s.ankle) - r.y(s.hip))) else null }
                // the standing leg stays under the body (up to ~10° on the videos) and the swinging leg is clearly further
                // out; a lunge or a split stance has both legs off vertical by about the same angle
                val a = legs.map { kotlin.math.abs(it) }
                if (legs.size < 2 || a.min() > 12.0 || a.max() - a.min() < 6.0) null else legs.maxByOrNull { kotlin.math.abs(it) }
            }
        }
        // facing the phone, feet planted: the hips travel side to side over the feet as they circle (hip centre
        // relative to the middle of the ankles, ±0.1 torso lengths on the rendered videos); one excursion across and
        // back is one circle (a circle takes ~2.5 s).
        CountedMove.HIP_CIRCLE -> {
            var footMovedMs = Long.MIN_VALUE / 2
            SignalRepCounter(+1, travel = 0.09, minRepMs = 500) { r ->
                val t = r.torso
                val la = Side.LEFT.ankle; val ra = Side.RIGHT.ankle
                val now = r.f.timestampMs
                if (t == null || t.tilt > 20.0 || (r.frontal() ?: 0.0) < 0.35 || !r.seenAt(0.5f, la, ra)) null
                else {
                    // both feet planted and apart: a foot lifted (marching, side leg raises) or travelling (skater steps)
                    // blocks the reading for longer than a tracking blip, so the circle in progress is dropped
                    if (kotlin.math.abs(r.y(la) - r.y(ra)) / t.len > 0.12 || kotlin.math.abs(r.x(la) - r.x(ra)) / t.len !in 0.25..1.0) footMovedMs = now
                    if (now - footMovedMs < 2 * MAX_BLIP_MS) null else (t.hx - (r.x(la) + r.x(ra)) / 2) / t.len
                }
            }
        }
        // standing: the heel comes up behind — the knee bends (hip–knee–ankle) from ~165° to ~110–130° in a quick kick
        CountedMove.BUTT_KICK -> SignalRepCounter(-1, travel = 25.0, minRepMs = 150, smoothingWindow = 2) { r ->
            if (!r.torsoIn(0.0, 35.0)) null else r.sides { s -> r.angle(s.hip, s.knee, s.ankle, 0.3f) }.minOrNull()
        }
        // facing the phone, hands together at the chest: turning carries the hands to either side of the hips
        CountedMove.TWIST -> TwoSidedRepCounter(travel = 0.12, minRepMs = 400) { r ->
            val t = r.torso
            if (t == null || t.tilt > 30.0 || (r.frontal() ?: 0.0) < 0.35 || !r.seen(Side.LEFT.wrist, Side.RIGHT.wrist)) null
            else ((r.x(Side.LEFT.wrist) + r.x(Side.RIGHT.wrist)) / 2 - t.hx) / t.len
        }
        // facing the phone: the shoulders lean sideways over the hips, to either side
        CountedMove.SIDE_BEND -> TwoSidedRepCounter(travel = 10.0, minRepMs = 500) { r -> r.torso?.takeIf { r.frontal()?.let { f -> f > 0.35 } == true }?.lean }
        // facing the phone: the hips travel sideways, to either side of the middle
        CountedMove.SKATE -> ZigZagRepCounter(travel = 0.35) { r -> r.torso?.let { t -> t.hx / t.len } }
        // standing side-on, hands on the wall at about shoulder height: the elbows bend
        CountedMove.WALL_PUSH_UP -> SignalRepCounter(-1, travel = 30.0, minRepMs = 500) { r ->
            if (!r.torsoIn(0.0, 45.0)) null
            else {
                // hands on the wall: about shoulder height and reaching forward of the shoulder (an arm swinging by the
                // side, as in a march, never reads)
                val arms = r.sides { s ->
                    if (r.seen(s.shoulder, s.elbow, s.wrist) && kotlin.math.abs(r.above(s.wrist, s.shoulder) ?: 9.0) < 0.5 &&
                        kotlin.math.abs(r.x(s.wrist) - r.x(s.shoulder)) / (r.torso?.len ?: 1.0) > 0.25
                    ) r.angle(s.shoulder, s.elbow, s.wrist) else null
                }
                arms.takeIf { it.isNotEmpty() }?.average()
            }
        }
        // lying on the back: the hands press up away from the shoulders
        CountedMove.FLOOR_PRESS -> SignalRepCounter(+1, travel = 0.25, minRepMs = 500) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> r.above(s.wrist, s.shoulder) }.maxOrNull()
        }
        // hands on a bench behind, torso upright: the elbows bend as the body lowers
        CountedMove.DIP -> SignalRepCounter(-1, travel = 30.0, minRepMs = 500) { r ->
            if (!r.torsoIn(0.0, 45.0)) null
            else r.sides { s -> if (r.seen(s.shoulder, s.elbow, s.wrist) && r.y(s.wrist) > r.y(s.shoulder)) r.angle(s.shoulder, s.elbow, s.wrist) else null }.maxOrNull()
        }
        // lying on the back: the shoulders curl up off the floor (the torso tilts up from flat)
        CountedMove.CRUNCH -> SignalRepCounter(-1, travel = 8.0, minRepMs = 500) { r ->
            if (!r.torsoIn(45.0, 120.0)) null else r.torso?.tilt
        }
        // lying on the back: the knees come in toward the chest (the hip angle closes)
        CountedMove.KNEES_IN -> SignalRepCounter(-1, travel = 15.0, minRepMs = 500) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> r.angle(s.shoulder, s.hip, s.knee, 0.3f) }.minOrNull()
        }
        // lying on the back, legs in tabletop: one foot lowers toward the floor (the lower ankle, below its knee)
        CountedMove.TOE_TAP -> SignalRepCounter(+1, travel = 0.20, minRepMs = 400) { r ->
            if (!r.torsoIn(60.0, 120.0)) null else r.sides { s -> if (r.seenAt(0.4f, s.knee, s.ankle)) -(r.above(s.ankle, s.knee) ?: return@sides null) else null }.maxOrNull()
        }
        // lying with the shoulders curled up, filmed side-on: the near hand slides toward its heel, then away as the
        // body reaches to the far side (distance hand to heel, in torso lengths; each reach to either side is a tap)
        CountedMove.HEEL_TAP -> TwoSidedRepCounter(travel = 0.045, minRepMs = 400) { r ->
            val t = r.torso
            if (t == null || !r.torsoIn(55.0, 120.0)) null
            else { val s = r.nearer({ it.wrist }, { it.ankle }); if (r.seenAt(0.4f, s.wrist, s.ankle)) r.dist(s.wrist, s.ankle) / t.len else null }
        }
        // plank: one hand lifts off the floor toward the other shoulder (rise of the higher wrist over the lower one)
        CountedMove.SHOULDER_TAP -> SignalRepCounter(+1, travel = 0.20, minRepMs = 300) { r ->
            val t = r.torso
            if (t == null || !r.torsoIn(55.0, 125.0) || !r.seenAt(0.3f, Side.LEFT.wrist, Side.RIGHT.wrist)) null
            else kotlin.math.abs(r.y(Side.LEFT.wrist) - r.y(Side.RIGHT.wrist)) / t.len
        }
        // kettlebell swing, side-on: the hips fold (shoulder–hip–knee closes from ~178° to ~95°) and snap open again;
        // a swing takes well under a second, too quick for the hinge counter's minimum
        CountedMove.SWING -> SignalRepCounter(-1, travel = 45.0, minRepMs = 300) { r ->
            if (!r.torsoIn(0.0, 70.0)) null else r.sides { s -> r.angle(s.shoulder, s.hip, s.knee, 0.4f) }.minOrNull()
        }
        // standing, facing the phone: the shoulders rise toward the ears (the nose gets closer above them), 0.05–0.07 torso
        // lengths on the rendered videos
        CountedMove.SHRUG -> SignalRepCounter(-1, travel = 0.04, minRepMs = 300) { r ->
            val t = r.torso
            if (t == null || t.tilt > 25.0 || !r.seen(BodyLandmark.NOSE)) null else (t.sy - r.y(BodyLandmark.NOSE)) / t.len
        }
        // on all fours, filmed from a front corner: the working knee moves away from the other knee — back and up for
        // donkey kicks, out to the side for fire hydrants (distance between the knees, ~0.1–0.4 torso lengths resting,
        // 0.8–1.1 lifted). Reads the same for both legs, while the far knee's height does not (perspective).
        CountedMove.KICK_BACK -> SignalRepCounter(+1, travel = 0.25, minRepMs = 500) { r ->
            val t = r.torso
            if (t == null || !r.torsoIn(55.0, 125.0) || !r.seenAt(0.3f, Side.LEFT.knee, Side.RIGHT.knee)) null
            else r.dist(Side.LEFT.knee, Side.RIGHT.knee) / t.len
        }
        // boxing pull-back, from a front corner: the head moves back off its line over the stance (nose relative to the
        // hips, in torso lengths, ~0.2 on the rendered videos); each pull to either side of the learnt middle is one
        CountedMove.PULL_BACK -> TwoSidedRepCounter(travel = 0.12, minRepMs = 250) { r ->
            val t = r.torso
            if (t == null || t.tilt > 40.0 || !r.seen(BodyLandmark.NOSE)) null else (r.x(BodyLandmark.NOSE) - t.hx) / t.len
        }
        // block then cross: counted once per block-and-counter like the combinations, with a lower lift (the block
        // raises the elbow 0.18–0.24 torso lengths, the cross at the phone less)
        CountedMove.BLOCK_COUNTER -> ComboRepCounter(travel = 0.15)
        else -> null
    }

}
