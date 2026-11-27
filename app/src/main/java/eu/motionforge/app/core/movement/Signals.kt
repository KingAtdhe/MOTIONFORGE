package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_ANKLE
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_ELBOW
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_FOOT_INDEX
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_HEEL
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_HIP
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_KNEE
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_SHOULDER
import eu.motionforge.app.core.pose.BodyLandmark.LEFT_WRIST
import eu.motionforge.app.core.pose.BodyLandmark.NOSE
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_ANKLE
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_ELBOW
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_FOOT_INDEX
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_HEEL
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_HIP
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_KNEE
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_SHOULDER
import eu.motionforge.app.core.pose.BodyLandmark.RIGHT_WRIST
import eu.motionforge.app.core.pose.PoseFrame
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.hypot

/**
 * Small measurements on one pose frame for the movement counters, in image pixels normalised by the torso length (so
 * body size and distance to the camera do not matter). Every function returns null when the points it needs are not
 * clearly visible: a counter then treats the frame as unreadable (never as a rep).
 */
class PoseReader(val f: PoseFrame, private val minVisibility: Float = 0.6f) {
    fun seen(vararg l: BodyLandmark) = l.all { f[it].visibility >= minVisibility }
    fun seenAt(v: Float, vararg l: BodyLandmark) = l.all { f[it].visibility >= v }
    fun x(l: BodyLandmark) = f[l].x * f.imageWidth.toDouble()
    fun y(l: BodyLandmark) = f[l].y * f.imageHeight.toDouble()
    fun dist(a: BodyLandmark, b: BodyLandmark) = hypot(x(a) - x(b), y(a) - y(b))

    /** Shoulder and hip centres (or the one side that is clearly seen, side-on) and the torso length. */
    val torso: Torso? by lazy {
        val left = seen(LEFT_SHOULDER, LEFT_HIP); val right = seen(RIGHT_SHOULDER, RIGHT_HIP)
        if (!left && !right) return@lazy null
        fun c(l: BodyLandmark, r: BodyLandmark, g: (BodyLandmark) -> Double) =
            if (left && right) (g(l) + g(r)) / 2 else if (left) g(l) else g(r)
        val t = Torso(c(LEFT_SHOULDER, RIGHT_SHOULDER, ::x), c(LEFT_SHOULDER, RIGHT_SHOULDER, ::y),
            c(LEFT_HIP, RIGHT_HIP, ::x), c(LEFT_HIP, RIGHT_HIP, ::y))
        if (t.len < 5.0) null else t
    }

    /** Angle at [b] (degrees) of a–b–c, or null. */
    fun angle(a: BodyLandmark, b: BodyLandmark, c: BodyLandmark, v: Float = minVisibility): Double? {
        if (!seenAt(v, a, b, c)) return null
        val ux = x(a) - x(b); val uy = y(a) - y(b); val vx = x(c) - x(b); val vy = y(c) - y(b)
        val n = hypot(ux, uy) * hypot(vx, vy)
        if (n < 1.0) return null
        return Math.toDegrees(acos(((ux * vx + uy * vy) / n).coerceIn(-1.0, 1.0)))
    }

    /** How far [a] is above [b] in the image, in torso lengths (positive = higher). */
    fun above(a: BodyLandmark, b: BodyLandmark): Double? {
        val t = torso ?: return null
        if (!seen(a, b)) return null
        return (y(b) - y(a)) / t.len
    }

    /** Shoulder width over torso length: ~0.5–0.7 facing the phone, small side-on. */
    fun frontal(): Double? {
        val t = torso ?: return null
        if (!seen(LEFT_SHOULDER, RIGHT_SHOULDER)) return null
        return dist(LEFT_SHOULDER, RIGHT_SHOULDER) / t.len
    }

    /** Values of [g] for the left and right side, skipping a side whose value is null. */
    fun <T> sides(g: (Side) -> T?): List<T> = listOfNotNull(g(Side.LEFT), g(Side.RIGHT))

    /** The side whose given joints are rated more visible (side-on: the one nearer the camera). */
    fun nearer(vararg joints: (Side) -> BodyLandmark): Side =
        if (joints.sumOf { f[it(Side.LEFT)].visibility.toDouble() } >= joints.sumOf { f[it(Side.RIGHT)].visibility.toDouble() }) Side.LEFT else Side.RIGHT
}

enum class Side(
    val shoulder: BodyLandmark, val elbow: BodyLandmark, val wrist: BodyLandmark, val hip: BodyLandmark,
    val knee: BodyLandmark, val ankle: BodyLandmark, val heel: BodyLandmark, val toe: BodyLandmark,
) {
    LEFT(LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, LEFT_HEEL, LEFT_FOOT_INDEX),
    RIGHT(RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE, RIGHT_HEEL, RIGHT_FOOT_INDEX),
}

data class Torso(val sx: Double, val sy: Double, val hx: Double, val hy: Double) {
    val len: Double get() = hypot(sx - hx, sy - hy)

    /** Angle from image vertical, degrees: 0 upright, 90 lying, 180 upside down. */
    val tilt: Double get() {
        val dy = hy - sy
        val a = Math.toDegrees(atan2(abs(sx - hx), abs(dy)))
        return if (dy < 0) 180.0 - a else a
    }

    /** Sideways lean of the shoulders over the hips (facing the phone), degrees, signed. */
    val lean: Double get() = Math.toDegrees(atan2(sx - hx, hy - sy))
}

/** A counter whose signal is a function of the pose (see [ExcursionRepCounter] for the counting rules). */
class SignalRepCounter(
    direction: Int,
    travel: Double,
    returnFraction: Double = 0.8,
    minRepMs: Long = 700,
    smoothingWindow: Int = 3,
    private val read: (PoseReader) -> Double?,
) : ExcursionRepCounter(direction, travel, returnFraction, minRepMs, smoothingWindow) {
    override fun signal(f: PoseFrame): Double? = read(PoseReader(f, minVisibility))
}

/** Like [SignalRepCounter] but each excursion to either side of a slowly learnt middle is a rep (twists, side bends,
 *  skater steps, slips). The middle follows the signal only while it is near it, so a held lean is not a new middle. */
class TwoSidedRepCounter(
    private val travel: Double,
    private val minRepMs: Long = 300,
    private val read: (PoseReader) -> Double?,
) : RepCounter {
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
        val raw = if (tracking) read(PoseReader(frame)) else null
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
                if (abs(x - base) < 0.5 * travel) base += 0.08 * (x - base)
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
}

/**
 * Side-to-side movements that go straight from one side to the other (skater steps): each traverse of at least
 * [travel] is one rep, counted when the movement settles at its far end ("you land") or turns back. A tracking gap
 * longer than [MAX_BLIP_MS] drops the traverse in progress.
 */
class ZigZagRepCounter(
    private val travel: Double,
    private val settle: Double = 0.02,
    private val minRepMs: Long = 250,
    private val read: (PoseReader) -> Double?,
) : RepCounter {
    private var count = 0
    private var anchor = 0.0
    private var extreme = 0.0
    private var dir = 0
    private var counted = false
    private var started = false
    private var startMs = 0L
    private var prev = 0.0
    private var lastGoodMs = -1L
    private val window = ArrayDeque<Double>()
    override val repetitions: Int get() = count

    override fun reset() { count = 0; lose() }
    private fun lose() { started = false; dir = 0; counted = false; window.clear(); lastGoodMs = -1L }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) read(PoseReader(frame)) else null
        if (raw == null) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, RepPhase.UNKNOWN, null)
            lose(); return RepUpdate(count, RepPhase.UNKNOWN, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > 3) window.removeFirst()
        val x = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null
        fun countIt() {
            if (!counted && t - startMs >= minRepMs) { count++; event = RepEvent.RepCompleted(count, emptySet()) }
            counted = true
        }
        if (!started) { started = true; anchor = x; extreme = x; prev = x; startMs = t }
        if (dir == 0) {
            if (abs(x - anchor) >= travel) { dir = if (x > anchor) 1 else -1; extreme = x }
        } else {
            if ((x - extreme) * dir > 0) extreme = x
            val far = abs(extreme - anchor) >= travel
            if (far && abs(x - prev) < settle && abs(x - extreme) < settle) countIt()
            if ((extreme - x) * dir >= 0.5 * travel) {
                if (far) countIt()
                anchor = extreme; dir = -dir; extreme = x; counted = false; startMs = t
            }
        }
        prev = x
        return RepUpdate(count, if (dir == 0) RepPhase.TOP else RepPhase.BOTTOM, x, event)
    }
}

/**
 * Pendulum movements (leg swings): the signed signal swings from one side of its middle (0) to the other. A swing is
 * counted when the signal reaches at least [side] on the opposite side of the last side it reached, having travelled
 * at least [travel] from its furthest point there. A movement that stays on one side and comes back (a lunge step,
 * a heel kicked up behind) never counts, and neither does a slow change of side (longer than [maxRepMs] from the
 * furthest point, as when stepping into and out of a split stance). A tracking gap longer than [MAX_BLIP_MS] forgets
 * the last side.
 */
class PendulumRepCounter(
    private val travel: Double,
    private val side: Double,
    private val minRepMs: Long = 250,
    private val maxRepMs: Long = 1_500,
    private val read: (PoseReader) -> Double?,
) : RepCounter {
    private var count = 0
    private var lastSide = 0
    private var extreme = 0.0
    private var sinceMs = 0L
    private var lastGoodMs = -1L
    private val window = ArrayDeque<Double>()
    override val repetitions: Int get() = count

    override fun reset() { count = 0; lose() }
    private fun lose() { lastSide = 0; window.clear(); lastGoodMs = -1L }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) read(PoseReader(frame)) else null
        if (raw == null) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, RepPhase.UNKNOWN, null)
            lose(); return RepUpdate(count, RepPhase.UNKNOWN, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > 2) window.removeFirst()
        val x = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null
        val s = if (x >= side) 1 else if (x <= -side) -1 else 0
        when {
            s == 0 -> {}
            lastSide == 0 -> { lastSide = s; extreme = x; sinceMs = t }
            s == lastSide -> if (abs(x) > abs(extreme)) { extreme = x; sinceMs = t }
            else -> {
                if (abs(x - extreme) >= travel && t - sinceMs in minRepMs..maxRepMs) { count++; event = RepEvent.RepCompleted(count, emptySet()) }
                lastSide = s; extreme = x; sinceMs = t
            }
        }
        return RepUpdate(count, if (s == 0) RepPhase.TOP else RepPhase.BOTTOM, x, event)
    }
}
