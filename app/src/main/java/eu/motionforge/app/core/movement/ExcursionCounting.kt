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

    private fun lose() {
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) signal(frame) else null
        if (raw == null) {
            lose()
            return RepUpdate(count, phase, null)
        }
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
 * Bent-over row: the wrists rise toward the hips/ribs while the body stays hinged. Signal: wrist height above the
 * hips, in torso lengths. Only while the torso is clearly tilted (a standing curl is not a row).
 */
class RowRepCounter(travel: Double = 0.22, private val minTilt: Double = 20.0) : ExcursionRepCounter(+1, travel) {
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
class HingeRepCounter(travel: Double = 30.0) : ExcursionRepCounter(+1, travel) {
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
 * Calf raise: the ankles rise above the toes. Signal: toe-to-ankle height over the shin length, averaged over the
 * visible feet. Only while standing upright.
 */
class CalfRaiseRepCounter(travel: Double = 0.07) : ExcursionRepCounter(+1, travel) {
    override fun signal(f: PoseFrame): Double? {
        val (s, h, _) = f.torso() ?: return null
        if (tilt(s, h) > 30.0) return null
        val feet = listOf(
            Triple(BodyLandmark.LEFT_KNEE, BodyLandmark.LEFT_ANKLE, BodyLandmark.LEFT_FOOT_INDEX),
            Triple(BodyLandmark.RIGHT_KNEE, BodyLandmark.RIGHT_ANKLE, BodyLandmark.RIGHT_FOOT_INDEX),
        ).filter { (k, a, t) -> f.seen(k, a, t) }.map { (k, a, t) -> (f.px(t).second - f.px(a).second) / f.dist(k, a).coerceAtLeast(1.0) }
        return if (feet.isEmpty()) null else feet.average()
    }
}
