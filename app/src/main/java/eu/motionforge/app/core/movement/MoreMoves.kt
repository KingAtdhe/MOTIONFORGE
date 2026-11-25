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
        CountedMove.CAT_COW -> SignalRepCounter(+1, travel = 0.12, minRepMs = 800) { r ->
            val t = r.torso
            if (t == null || !r.torsoIn(60.0, 120.0) || !r.seen(BodyLandmark.NOSE)) null else (t.sy - r.y(BodyLandmark.NOSE)) / t.len
        }
        // standing: the working leg swings away from vertical (hip→ankle), back for kickbacks, out for side raises
        CountedMove.LEG_SWING -> SignalRepCounter(+1, travel = 15.0, minRepMs = 500) { r ->
            if (!r.torsoIn(0.0, 35.0)) null
            else r.sides { s -> if (r.seenAt(0.4f, s.hip, s.ankle)) Math.toDegrees(kotlin.math.atan2(kotlin.math.abs(r.x(s.ankle) - r.x(s.hip)), r.y(s.ankle) - r.y(s.hip))) else null }.maxOrNull()
        }
        // standing: the heel comes up behind — the knee bends (hip–knee–ankle) from ~165° to ~110–130° in a quick kick
        CountedMove.BUTT_KICK -> SignalRepCounter(-1, travel = 25.0, minRepMs = 150, smoothingWindow = 2) { r ->
            if (!r.torsoIn(0.0, 35.0)) null else r.sides { s -> r.angle(s.hip, s.knee, s.ankle, 0.4f) }.minOrNull()
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
        // standing, hands on the wall at about shoulder height: the elbows bend
        CountedMove.WALL_PUSH_UP -> SignalRepCounter(-1, travel = 30.0, minRepMs = 500) { r ->
            if (!r.torsoIn(0.0, 45.0)) null
            else {
                val arms = r.sides { s -> if (r.seen(s.shoulder, s.elbow, s.wrist) && kotlin.math.abs(r.above(s.wrist, s.shoulder) ?: 9.0) < 0.5) r.angle(s.shoulder, s.elbow, s.wrist) else null }
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
        CountedMove.HEEL_TAP -> TwoSidedRepCounter(travel = 0.07, minRepMs = 400) { r ->
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
        // standing, facing the phone: the shoulders rise toward the ears (the nose gets closer above them), ~0.07 torso
        // lengths on the rendered videos
        CountedMove.SHRUG -> SignalRepCounter(-1, travel = 0.045, minRepMs = 500) { r ->
            val t = r.torso
            if (t == null || t.tilt > 25.0 || !r.seen(BodyLandmark.NOSE)) null else (t.sy - r.y(BodyLandmark.NOSE)) / t.len
        }
        // on all fours: the working knee lifts off the floor (back for donkey kicks, out to the side for hydrants)
        CountedMove.KICK_BACK -> SignalRepCounter(+1, travel = 0.20, minRepMs = 500) { r ->
            if (!r.torsoIn(55.0, 125.0)) null else r.sides { s -> if (r.seenAt(0.3f, s.knee, s.hip)) r.above(s.knee, s.hip) else null }.maxOrNull()
        }
        else -> null
    }

}
