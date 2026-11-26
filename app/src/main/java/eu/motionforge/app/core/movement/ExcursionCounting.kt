package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.PoseFrame
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.hypot

/**
 * Counter for movements that leave a resting position and come back: one rep is the signal moving at least
 * [travel] away from rest in [direction] (+1 up, −1 down), then coming back from its furthest point by at least
 * [returnFraction] × [travel]. (Measured from the furthest point, not back to rest: a shoulder press starts at the
 * shoulders, not from the arms hanging before the set.)
 * The resting value is learnt from the person (lowest/highest value since the last rep), so body size, camera
 * distance and where exactly someone holds the weights don't matter. Same safety rules as the other counters: a
 * frame that can't be read (or tracking off) drops the cycle, and a cycle faster than [minRepMs] is ignored.
 * Thresholds are set from the rendered test videos (docs/BUILD_LOG.md), for coach review.
 */
abstract class ExcursionRepCounter(
    private val direction: Int,
    private val travel: Double,
    private val returnFraction: Double = 0.8,
    private val minRepMs: Long = 700,
    private val smoothingWindow: Int = 3,
    protected val minVisibility: Float = 0.6f,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN
    private var rest = 0.0
    private var extreme = 0.0
    private var outSinceMs = 0L
    private val window = ArrayDeque<Double>()

    override val repetitions: Int get() = count

    /** The movement's signal for this frame, or null when it can't be read (or the body is not in position). */
    protected abstract fun signal(f: PoseFrame): Double?

    override fun reset() {
        count = 0
        lose()
    }

    private var lastGoodMs = -1L

    private fun lose() {
        lastGoodMs = -1L
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) signal(frame) else null
        if (raw == null) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, phase, null)
            lose()
            return RepUpdate(count, phase, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val v = window.average()
        val x = direction * v
        val t = frame.timestampMs
        var event: RepEvent? = null
        when (phase) {
            RepPhase.UNKNOWN -> { phase = RepPhase.TOP; rest = x }
            RepPhase.TOP -> {
                rest = minOf(rest, x)
                if (x > rest + travel) { phase = RepPhase.BOTTOM; extreme = x; outSinceMs = t }
            }
            RepPhase.DESCENDING, RepPhase.BOTTOM -> {
                extreme = maxOf(extreme, x)
                if (x < extreme - returnFraction * travel) {
                    if (t - outSinceMs >= minRepMs) {
                        count++
                        event = RepEvent.RepCompleted(count, emptySet())
                    }
                    phase = RepPhase.TOP; rest = x
                }
            }
        }
        return RepUpdate(count, phase, v, event)
    }

    // ---- shared pose measurements (pixels) ----
    protected fun PoseFrame.seen(vararg l: BodyLandmark) = l.all { this[it].visibility >= minVisibility }
    protected fun PoseFrame.px(l: BodyLandmark) = (this[l].x * imageWidth.toDouble()) to (this[l].y * imageHeight.toDouble())
    protected fun PoseFrame.dist(a: BodyLandmark, b: BodyLandmark): Double {
        val (ax, ay) = px(a); val (bx, by) = px(b); return hypot(ax - bx, ay - by)
    }
    protected fun PoseFrame.midOf(a: BodyLandmark, b: BodyLandmark): Pair<Double, Double> {
        val (ax, ay) = px(a); val (bx, by) = px(b); return ((ax + bx) / 2) to ((ay + by) / 2)
    }

    /** Shoulder-mid and hip-mid in pixels and the torso length, or null when the torso isn't clearly seen. */
    protected fun PoseFrame.torso(): Triple<Pair<Double, Double>, Pair<Double, Double>, Double>? {
        if (!seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val s = midOf(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER)
        val h = midOf(BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)
        val len = hypot(s.first - h.first, s.second - h.second)
        return if (len < 5.0) null else Triple(s, h, len)
    }

    /** Torso angle from image vertical, degrees. */
    protected fun tilt(s: Pair<Double, Double>, h: Pair<Double, Double>): Double {
        val dy = h.second - s.second
        val a = Math.toDegrees(atan2(abs(s.first - h.first), abs(dy)))
        return if (dy < 0) 180.0 - a else a
    }

    protected companion object {
        val ARMS = listOf(
            Triple(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_ELBOW, BodyLandmark.LEFT_WRIST),
            Triple(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_ELBOW, BodyLandmark.RIGHT_WRIST),
        )
    }
}

/**
 * Arm lifts (biceps curl, shoulder press, lateral raise, step jack arms): how high the wrists are above the shoulders,
 * in torso lengths, averaged over the visible arms. Reads the same from any side, unlike the elbow angle (a curl seen
 * from the front bends toward the camera). Only while standing fairly upright.
 */
class ArmLiftRepCounter(travel: Double, private val maxTilt: Double = 40.0, minRepMs: Long = 700) :
    ExcursionRepCounter(+1, travel, minRepMs = minRepMs) {
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        if (tilt(s, h) > maxTilt) return null
        val lifts = ARMS.filter { (sh, _, wr) -> f.seen(sh, wr) }.map { (sh, _, wr) -> (f.px(sh).second - f.px(wr).second) / len }
        return if (lifts.isEmpty()) null else lifts.average()
    }
}

/**
 * Overhead triceps extension: the arms start straight overhead and the hands drop behind the head. Signal: wrist
 * height above the shoulders, in torso lengths (as [ArmLiftRepCounter]), counted downward — one rep is the hands
 * dropping by [travel] and pressing back up. Raising the weights from the sides into the start position is a rise,
 * not a drop, so it never counts; with the hands below the shoulders nothing is read at all.
 */
class OverheadDropRepCounter(travel: Double = 0.30, private val maxTilt: Double = 30.0) : ExcursionRepCounter(-1, travel) {
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        if (tilt(s, h) > maxTilt) return null
        val lifts = ARMS.filter { (sh, _, wr) -> f.seen(sh, wr) }.map { (sh, _, wr) -> (f.px(sh).second - f.px(wr).second) / len }
        if (lifts.isEmpty()) return null
        val v = lifts.average()
        // Only with the hands above the shoulders (the bottom of a rep is still ~0.17 above): a curl or a lowered
        // arm never reads as a triceps rep.
        return if (v < 0.0) null else v
    }
}

/**
 * Knee lifts (high-knee march, standing knee crunch): how high the higher knee comes toward the hips, in torso
 * lengths (about −0.9 standing, about 0 with the thigh level). Each lift of either knee is one rep. Measured against
 * the hips, so a small forward curl of the chest (knee crunch) doesn't change it. Lifts are quick (the thigh is above
 * the half-way mark for only ~0.2–0.3 s), hence the short minimum; side-on the far knee is tracked but rated only
 * ~0.5 visible, so knees are accepted from [kneeVisibility] (the travel, ~half a torso, is far above landmark noise).
 */
class KneeLiftRepCounter(travel: Double = 0.45, private val kneeVisibility: Float = 0.4f) :
    ExcursionRepCounter(+1, travel, minRepMs = 150) {
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        if (tilt(s, h) > 40.0) return null
        val knees = listOf(BodyLandmark.LEFT_KNEE, BodyLandmark.RIGHT_KNEE).filter { f[it].visibility >= kneeVisibility }
            .map { (h.second - f.px(it).second) / len }
        if (knees.isEmpty()) return null
        // Both knees high toward the hips is a squat, not a knee lift (a lift keeps the standing knee ~0.9 below).
        if (knees.size == 2 && knees.min() > -0.6) return null
        return knees.max()
    }
}

/**
 * Bent-over row: the wrists rise toward the hips/ribs while the body stays hinged. Signal: wrist height above the
 * hips, in torso lengths. Only while the torso is clearly tilted (a standing curl is not a row).
 */
class RowRepCounter(travel: Double = 0.22, private val minTilt: Double = 20.0) : ExcursionRepCounter(+1, travel, minRepMs = 500) {
    private var standingTorso = 0.0
    override fun reset() { super.reset(); standingTorso = 0.0 }
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        standingTorso = maxOf(standingTorso, len)
        // hinged: tilted in the image, or (filmed from the front) the torso foreshortened
        val pitch = maxOf(tilt(s, h), Math.toDegrees(acos((len / standingTorso).coerceIn(0.0, 1.0))))
        if (pitch < minTilt) return null
        val wrists = ARMS.filter { (_, _, wr) -> f.seen(wr) }.map { (_, _, wr) -> (h.second - f.px(wr).second) / len }
        return if (wrists.isEmpty()) null else wrists.average()
    }
}

/**
 * Band pull-apart: how far apart the wrists are, in shoulder widths. Only filmed roughly from the front (side-on the
 * hands move along the line of sight).
 */
class BandPullRepCounter(travel: Double = 0.6, private val minFrontal: Double = 0.45) : ExcursionRepCounter(+1, travel) {
    override fun signal(f: PoseFrame): Double? {
        val (_, _, len) = f.torso() ?: return null
        val sw = f.dist(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER)
        if (sw / len < minFrontal || !f.seen(BodyLandmark.LEFT_WRIST, BodyLandmark.RIGHT_WRIST)) return null
        return abs(f.px(BodyLandmark.LEFT_WRIST).first - f.px(BodyLandmark.RIGHT_WRIST).first) / sw
    }
}

/**
 * Hip hinge family (hip hinge, Romanian deadlift, kettlebell deadlift): how far the torso pitches forward, degrees.
 * Seen from the side that is the torso's tilt in the image; seen from the front the torso leans toward the camera and
 * looks shorter instead, so the pitch is the larger of the tilt and acos(torso length / standing torso length).
 */
class HingeRepCounter(travel: Double = 25.0) : ExcursionRepCounter(+1, travel, minRepMs = 500) {
    private var standingTorso = 0.0
    override fun reset() { super.reset(); standingTorso = 0.0 }
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        standingTorso = maxOf(standingTorso, len)
        return maxOf(tilt(s, h), Math.toDegrees(acos((len / standingTorso).coerceIn(0.0, 1.0))))
    }
}

/** Glute bridge: the hip angle (shoulder–hip–knee, the side nearer the camera) opens as the hips lift. */
class BridgeRepCounter(travel: Double = 20.0) : ExcursionRepCounter(+1, travel) {
    override fun signal(f: PoseFrame): Double? {
        val left = f[BodyLandmark.LEFT_HIP].visibility + f[BodyLandmark.LEFT_KNEE].visibility >=
            f[BodyLandmark.RIGHT_HIP].visibility + f[BodyLandmark.RIGHT_KNEE].visibility
        val (sh, hp, kn) = if (left) Triple(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.LEFT_KNEE)
        else Triple(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_HIP, BodyLandmark.RIGHT_KNEE)
        if (!f.seen(sh, hp, kn)) return null
        // lying down: the torso is far from upright
        val (s, h, _) = f.torso() ?: return null
        if (tilt(s, h) < 50.0) return null
        val (ax, ay) = f.px(sh); val (bx, by) = f.px(hp); val (cx, cy) = f.px(kn)
        val u = (ax - bx) to (ay - by); val v = (cx - bx) to (cy - by)
        val d = hypot(u.first, u.second) * hypot(v.first, v.second)
        if (d < 1.0) return null
        return Math.toDegrees(acos(((u.first * v.first + u.second * v.second) / d).coerceIn(-1.0, 1.0)))
    }
}

/**
 * Calf raise, filmed side-on: how far the heel of the foot nearer the camera rises above its toes, in torso lengths
 * (rendered videos: ~0.04 flat, ~0.13 at the top). Only while standing upright with straight knees (a squat's heel
 * shift never reads as a raise). From the front the heel hides behind the foot: the card asks for a side view.
 */
class CalfRaiseRepCounter(travel: Double = 0.05) : ExcursionRepCounter(+1, travel, returnFraction = 0.7, minRepMs = 400) {
    override fun signal(f: PoseFrame): Double? {
        val r = PoseReader(f, minVisibility)
        val t = r.torso ?: return null
        if (t.tilt > 30.0) return null
        val s = r.nearer({ it.heel }, { it.toe }, { it.knee })
        val knee = r.angle(s.hip, s.knee, s.ankle) ?: return null
        if (knee < 150.0) return null
        return r.above(s.heel, s.toe)
    }
}

/**
 * Hooks and uppercuts: the punching elbow comes up from the guard (tucked, ~0.4–0.5 torso lengths below the
 * shoulder) toward shoulder height. Signal: the higher of the visible elbows, above the shoulders, in torso lengths.
 * The arm doesn't straighten in these punches, so the jab's reach rule can't see them.
 */
class PunchRepCounter(travel: Double = 0.20) : ExcursionRepCounter(+1, travel, minRepMs = 250) {
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        if (tilt(s, h) > 40.0) return null
        val lifts = ARMS.filter { (sh, el, _) -> f.seen(sh, el) }.map { (sh, el, _) -> (f.px(sh).second - f.px(el).second) / len }
        return lifts.maxOrNull()
    }

    /** The punch signal for [ComboRepCounter]: the higher visible elbow above the shoulders, in torso lengths. */
    internal fun elbowLift(f: PoseFrame): Double? = signal(f)
}

/**
 * Body jab: counted from the level change — the shoulders lowering toward the feet by [travel] (in the largest torso
 * length seen) and coming back up. A jab thrown straight at the phone barely moves in the picture (the elbow rises
 * ~0.12 torso lengths from the front, against 0.2 needed), so the punch itself is not what is counted; the bend of the
 * knees is (~0.17 from the front and 3/4). Ankles from 0.5 visible (the far ankle is often hidden in 3/4).
 */
class LevelChangeRepCounter(travel: Double = 0.10) : ExcursionRepCounter(-1, travel, minRepMs = 300) {
    private var standingTorso = 0.0
    override fun reset() { super.reset(); standingTorso = 0.0 }
    override fun signal(f: PoseFrame): Double? {
        val (s, h, len) = f.torso() ?: return null
        if (tilt(s, h) > 40.0) return null
        val ankles = listOf(BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE).filter { f[it].visibility >= 0.5f }
        if (ankles.isEmpty()) return null
        standingTorso = maxOf(standingTorso, len)
        return (ankles.map { f.px(it).second }.average() - s.second) / standingTorso
    }
}

/**
 * Three-punch combinations (jab-jab-cross), counted once per combination. Same signal as [PunchRepCounter], but a
 * combination ends only when the elbows have been back near the guard (within [near] × [travel] of it) for
 * [holdMs]: between punches inside a combination the guard lasts ~0.1–0.2 s, after it ~1 s. Counting each punch
 * was tried and dropped — in the retimed clips the jab's return and the next punch overlap at the elbows.
 */
class ComboRepCounter(
    private val travel: Double = 0.20,
    private val near: Double = 0.35,
    private val holdMs: Long = 400,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN
    private var rest = 0.0
    private var quietSinceMs = -1L
    private var lastGoodMs = -1L
    private val window = ArrayDeque<Double>()
    private val punch = PunchRepCounter(travel)
    override val repetitions: Int get() = count

    override fun reset() { count = 0; lose() }
    private fun lose() { phase = RepPhase.UNKNOWN; window.clear(); lastGoodMs = -1L; quietSinceMs = -1L }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) punch.elbowLift(frame) else null
        if (raw == null) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, phase, null)
            lose(); return RepUpdate(count, phase, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > 3) window.removeFirst()
        val x = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null
        when (phase) {
            RepPhase.UNKNOWN -> { phase = RepPhase.TOP; rest = x }
            RepPhase.TOP -> {
                rest = minOf(rest, x)
                if (x > rest + travel) { phase = RepPhase.BOTTOM; quietSinceMs = -1L }
            }
            RepPhase.DESCENDING, RepPhase.BOTTOM -> {
                if (x < rest + near * travel) {
                    if (quietSinceMs < 0) quietSinceMs = t
                    if (t - quietSinceMs >= holdMs) {
                        count++; event = RepEvent.RepCompleted(count, emptySet())
                        phase = RepPhase.TOP; rest = x
                    }
                } else quietSinceMs = -1L
            }
        }
        return RepUpdate(count, phase, x, event)
    }
}

/**
 * Slips: the head moves sideways off its resting line (nose relative to the hips, in torso lengths). The resting line
 * is learnt slowly while the head is in the middle, so a stance that leans a little to one side doesn't count; each
 * slip to either side is one rep.
 */
class SlipRepCounter(private val travel: Double = 0.10, private val minRepMs: Long = 250) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN
    private var base = 0.0
    private var extreme = 0.0
    private var outSinceMs = 0L
    private var lastGoodMs = -1L
    private val window = ArrayDeque<Double>()
    override val repetitions: Int get() = count

    override fun reset() { count = 0; lose() }
    private fun lose() { phase = RepPhase.UNKNOWN; window.clear(); lastGoodMs = -1L }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) lateral(frame) else null
        if (raw == null) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, phase, null)
            lose(); return RepUpdate(count, phase, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > 3) window.removeFirst()
        val x = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null
        when (phase) {
            RepPhase.UNKNOWN -> { phase = RepPhase.TOP; base = x }
            RepPhase.TOP -> {
                base += 0.08 * (x - base)                                     // slow: follows the stance, not a slip
                if (abs(x - base) > travel) { phase = RepPhase.BOTTOM; extreme = abs(x - base); outSinceMs = t }
            }
            RepPhase.DESCENDING, RepPhase.BOTTOM -> {
                val d = abs(x - base)
                extreme = maxOf(extreme, d)
                if (d < extreme - 0.8 * travel) {
                    if (t - outSinceMs >= minRepMs) { count++; event = RepEvent.RepCompleted(count, emptySet()) }
                    phase = RepPhase.TOP
                }
            }
        }
        return RepUpdate(count, phase, x, event)
    }

    private fun lateral(f: PoseFrame): Double? {
        val vis = { l: BodyLandmark -> f[l].visibility >= 0.6f }
        if (!listOf(BodyLandmark.NOSE, BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP).all(vis)) return null
        val w = f.imageWidth.toDouble(); val h = f.imageHeight.toDouble()
        val sx = (f[BodyLandmark.LEFT_SHOULDER].x + f[BodyLandmark.RIGHT_SHOULDER].x) / 2.0 * w
        val sy = (f[BodyLandmark.LEFT_SHOULDER].y + f[BodyLandmark.RIGHT_SHOULDER].y) / 2.0 * h
        val hx = (f[BodyLandmark.LEFT_HIP].x + f[BodyLandmark.RIGHT_HIP].x) / 2.0 * w
        val hy = (f[BodyLandmark.LEFT_HIP].y + f[BodyLandmark.RIGHT_HIP].y) / 2.0 * h
        val len = hypot(sx - hx, sy - hy)
        if (len < 5.0) return null
        return (f[BodyLandmark.NOSE].x * w - hx) / len
    }
}
