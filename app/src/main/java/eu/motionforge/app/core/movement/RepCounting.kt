package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseGeometry
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot

/** A form adjustment a rep counter can name. [message] is shown on screen, [spoken] is said by the voice coach. */
interface FormCue {
    val message: String
    val spoken: String
}

/** Where a counted movement is in its cycle: TOP is the start/end position (standing, arms straight). */
enum class RepPhase { UNKNOWN, TOP, DESCENDING, BOTTOM }

/** Something worth telling the person about, produced once at the end of a movement cycle. */
sealed interface RepEvent {
    /** A counted repetition; [issues] in priority order, empty when no rule found anything to adjust. */
    data class RepCompleted(val rep: Int, val issues: Set<FormCue>) : RepEvent

    /** A clear dip that did not reach counting depth and was not counted. */
    data object ShallowRep : RepEvent
}

/** [angle] is the movement's measured signal: knee angle (squat), elbow angle (push-up), hip height vs standing (lunge). */
data class RepUpdate(val count: Int, val phase: RepPhase, val angle: Double?, val event: RepEvent? = null)

interface RepCounter {
    val repetitions: Int
    fun reset()
    fun update(frame: PoseFrame, tracking: Boolean): RepUpdate
}

/** The movements the camera can count, with the words the coaching card uses for them. */
enum class CountedMove(val checkName: String, val framing: String, val idle: String, val shallow: String) {
    SQUAT("Squat check", "Keep your whole body in view, side-on or facing the phone.",
        "Lower with control. Each rep is checked when you stand up.",
        "That dip didn't reach counting depth. Go a little lower if it's comfortable."),
    PUSH_UP("Push-up check", "Put the phone on the floor side-on or at an angle, whole body in view.",
        "Lower with control. Each rep is checked when your arms are straight again.",
        "That one didn't reach counting depth. Lower your chest a little more if it's comfortable."),
    LUNGE("Lunge check", "Keep your whole body in view, side-on or facing the phone.",
        "Step back and lower with control. Each lunge is counted when you stand tall.",
        "That lunge didn't reach counting depth. Bend the knees a little more if it's comfortable."),
    ;

    companion object {
        /** Which counter a lesson uses, or null when the camera does not count that lesson. */
        fun forExercise(id: String): CountedMove? = when (id) {
            "bodyweight_squat", "sumo_squat" -> SQUAT
            "push_up", "knee_push_up", "incline_push_up" -> PUSH_UP
            "reverse_lunge", "split_squat" -> LUNGE
            else -> null
        }

        fun counterFor(id: String): RepCounter? = when (forExercise(id)) {
            SQUAT -> SquatRepCounter()
            PUSH_UP -> PushUpRepCounter(bodyLineToKnees = id == "knee_push_up")
            LUNGE -> LungeRepCounter()
            null -> null
        }
    }
}

/**
 * Shared repetition engine: one rep is a full cycle  top → bottom → top  of a smoothed joint angle.
 * Same safety rules as the squat counter: a frame without the needed landmarks (or with tracking off) resets the
 * cycle, so a rep can never be completed across a tracking gap; a cycle faster than [minRepMs] is ignored; a form
 * rule needs [minRuleFrames] qualifying bottom frames and most of them before it becomes a cue.
 */
abstract class CycleRepCounter(
    private val topAngle: Double,
    private val bottomAngle: Double,
    private val shallowAngle: Double,
    private val minRepMs: Long = 700,
    private val smoothingWindow: Int = 3,
    protected val minVisibility: Float = 0.6f,
    protected val minRuleFrames: Int = 3,
    protected val ruleFraction: Double = 0.6,
    /** How far below [topAngle] the signal must go before a descent starts (same units as the signal). */
    private val descentMargin: Double = 10.0,
    /** Frames within this much of [bottomAngle] are "at the bottom" for the form rules. */
    private val bottomBand: Double = 8.0,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN

    /** Where the current cycle is (subclasses that normalise their signal need it). */
    protected val currentPhase: RepPhase get() = phase
    private var cycleStartMs = 0L
    private var minAngle = 180.0
    private val window = ArrayDeque<Double>()

    override val repetitions: Int get() = count

    /** The movement's angle in this frame, or null when it cannot be measured (or the body is not in position). */
    protected abstract fun angle(f: PoseFrame): Double?

    /** Called for frames near the bottom of the cycle, to collect form measurements. */
    protected open fun observeBottom(f: PoseFrame) {}

    /** The cues for the cycle that just ended; called once per counted rep. */
    protected open fun cuesOfCycle(): Set<FormCue> = emptySet()

    /** Clears the per-cycle form measurements. */
    protected open fun startCycle() {}

    override fun reset() {
        count = 0
        lose()
    }

    private fun lose() {
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) angle(frame) else null
        if (raw == null) {
            lose()
            return RepUpdate(count, phase, null)
        }
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val a = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null
        if (phase == RepPhase.DESCENDING || phase == RepPhase.BOTTOM) minAngle = minOf(minAngle, a)
        when (phase) {
            RepPhase.UNKNOWN -> if (a >= topAngle) phase = RepPhase.TOP
            RepPhase.TOP -> if (a < topAngle - descentMargin) {
                phase = RepPhase.DESCENDING
                cycleStartMs = t
                minAngle = a
                startCycle()
            }
            RepPhase.DESCENDING -> when {
                a <= bottomAngle -> phase = RepPhase.BOTTOM
                a >= topAngle -> {
                    if (minAngle <= shallowAngle) event = RepEvent.ShallowRep
                    phase = RepPhase.TOP
                }
            }
            RepPhase.BOTTOM -> if (a >= topAngle) {
                if (t - cycleStartMs >= minRepMs) {
                    count++
                    event = RepEvent.RepCompleted(count, cuesOfCycle())
                }
                phase = RepPhase.TOP
            }
        }
        if (phase == RepPhase.BOTTOM && a <= bottomAngle + bottomBand) observeBottom(frame)
        return RepUpdate(count, phase, a, event)
    }

    protected fun PoseFrame.visible(vararg l: BodyLandmark) = l.all { this[it].visibility >= minVisibility }

    protected fun PoseFrame.px(a: Landmark, b: Landmark) = hypot((a.x - b.x) * imageWidth.toDouble(), (a.y - b.y) * imageHeight.toDouble())

    protected fun PoseFrame.angleAt(a: BodyLandmark, b: BodyLandmark, c: BodyLandmark): Double? =
        if (visible(a, b, c)) PoseGeometry.angleDegrees2d(this[a], this[b], this[c], imageWidth, imageHeight) else null

    /** Mid-point of two landmarks in pixels. */
    protected fun PoseFrame.mid(a: BodyLandmark, b: BodyLandmark) =
        ((this[a].x + this[b].x) / 2.0 * imageWidth) to ((this[a].y + this[b].y) / 2.0 * imageHeight)

    /** Angle of the hip→shoulder line from image vertical, degrees (0 = upright, 90 = lying flat). */
    protected fun PoseFrame.torsoFromVertical(): Double? {
        if (!visible(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER) &&
            !(visible(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_HIP) || visible(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_HIP))
        ) return null
        val s = mid(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER)
        val h = mid(BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)
        return Math.toDegrees(atan2(abs(s.first - h.first), h.second - s.second)).let { if (h.second - s.second < 0) 180.0 - it else it }
    }

    /** Shoulder width over torso length: large when the person faces the camera, small when side-on. */
    protected fun PoseFrame.frontalRatio(): Double? {
        if (!visible(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val torso = (px(this[BodyLandmark.LEFT_SHOULDER], this[BodyLandmark.LEFT_HIP]) + px(this[BodyLandmark.RIGHT_SHOULDER], this[BodyLandmark.RIGHT_HIP])) / 2
        if (torso < 5.0) return null
        return px(this[BodyLandmark.LEFT_SHOULDER], this[BodyLandmark.RIGHT_SHOULDER]) / torso
    }

}

enum class PushUpIssue(override val message: String, override val spoken: String) : FormCue {
    HIPS_SAG("Possible form adjustment: lift your hips into one line with your shoulders.", "Hips up into a line."),
    HIPS_PIKE("Possible form adjustment: lower your hips into one line with your shoulders.", "Hips down a little."),
}

/**
 * Push-up counter: the elbow angle (shoulder–elbow–wrist, averaged over the clearly visible arms) cycles from
 * straight ([topAngle]) to bent ([bottomAngle]). Only measured while the body is in a push-up position: the torso
 * clearly away from upright ([minTorsoTilt] from vertical, side-ish views) or strongly foreshortened (head-on
 * views), and the wrists below the shoulders — so arm movements while standing are never counted.
 *
 * Form rule, side-on only, at the bottom: the shoulder–hip–ankle line (shoulder–hip–knee for knee push-ups) bends
 * more than [maxLineBend]; the hips below that line → [PushUpIssue.HIPS_SAG], above → [PushUpIssue.HIPS_PIKE].
 * Thresholds are first hypotheses for coach review, checked against rendered test videos (see docs/BUILD_LOG.md).
 */
class PushUpRepCounter(
    private val bodyLineToKnees: Boolean = false,
    topAngle: Double = 150.0,
    bottomAngle: Double = 105.0,
    shallowAngle: Double = 130.0,
    private val minTorsoTilt: Double = 45.0,
    private val maxForeshortened: Double = 0.75,
    private val maxLineBend: Double = 15.0,
) : CycleRepCounter(topAngle, bottomAngle, shallowAngle) {
    private var sideBottom = 0
    private var sag = 0
    private var pike = 0

    override fun startCycle() { sideBottom = 0; sag = 0; pike = 0 }

    override fun angle(f: PoseFrame): Double? {
        val arms = listOfNotNull(
            f.angleAt(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_ELBOW, BodyLandmark.LEFT_WRIST),
            f.angleAt(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_ELBOW, BodyLandmark.RIGHT_WRIST),
        )
        if (arms.isEmpty() || !inPosition(f)) return null
        return arms.average()
    }

    private fun inPosition(f: PoseFrame): Boolean {
        val tilt = f.torsoFromVertical() ?: return false
        val wristsBelow = listOf(
            BodyLandmark.LEFT_SHOULDER to BodyLandmark.LEFT_WRIST, BodyLandmark.RIGHT_SHOULDER to BodyLandmark.RIGHT_WRIST,
        ).filter { (s, w) -> f.visible(s, w) }.let { pairs -> pairs.isNotEmpty() && pairs.all { (s, w) -> f[w].y > f[s].y } }
        if (!wristsBelow) return false
        if (tilt >= minTorsoTilt) return true
        val fr = f.frontalRatio() ?: return false
        return fr >= 1.0 / maxForeshortened // head-on: the torso is foreshortened to well under the shoulder width
    }

    override fun observeBottom(f: PoseFrame) {
        val fr = f.frontalRatio() ?: return
        if (fr > 0.45) return // only side-ish views show the body line
        val far = if (bodyLineToKnees) BodyLandmark.LEFT_KNEE to BodyLandmark.RIGHT_KNEE else BodyLandmark.LEFT_ANKLE to BodyLandmark.RIGHT_ANKLE
        // the side nearer the camera (higher visibility) gives the cleaner line
        val left = f[BodyLandmark.LEFT_HIP].visibility + f[far.first].visibility >= f[BodyLandmark.RIGHT_HIP].visibility + f[far.second].visibility
        val sh = if (left) BodyLandmark.LEFT_SHOULDER else BodyLandmark.RIGHT_SHOULDER
        val hp = if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP
        val end = if (left) far.first else far.second
        val ang = f.angleAt(sh, hp, end) ?: return
        sideBottom++
        if (180.0 - ang > maxLineBend) {
            // which side of the shoulder→end line the hip is on (image y grows downward)
            val s = f[sh]; val h = f[hp]; val e = f[end]
            val tt = ((h.x - s.x) / (e.x - s.x).let { if (abs(it) < 1e-6) 1e-6f else it }).coerceIn(0f, 1f)
            val lineY = s.y + (e.y - s.y) * tt
            if (h.y > lineY) sag++ else pike++
        }
    }

    override fun cuesOfCycle(): Set<FormCue> = buildSet {
        if (sideBottom >= minRuleFrames) {
            if (sag >= ruleFraction * sideBottom) add(PushUpIssue.HIPS_SAG)
            else if (pike >= ruleFraction * sideBottom) add(PushUpIssue.HIPS_PIKE)
        }
    }
}

enum class LungeIssue(override val message: String, override val spoken: String) : FormCue {
    LEANING("Possible form adjustment: keep your chest tall as you lower.", "Chest tall."),
}

/**
 * Lunge counter (reverse lunge, split squat). The signal is how high the hips are: the vertical distance from the
 * hips down to the lower ankle, over the torso length (so distance to the camera does not matter), relative to the
 * highest value seen since the counter started (standing tall). Unlike the knee angle this reads the same from the
 * front, the side and the diagonal: a knee bending toward the camera looks straight in a 2D image.
 *
 * A rep is a dip and a recovery measured from the cycle's own high point, not from standing: the hips drop at least
 * [drop] (fraction of standing hip height) below the last high point, then rise at least [rise] above the lowest
 * point. That works both for reverse lunges (back to standing each time) and split squats (the high point between
 * reps is the split stance, ~0.8 of standing). Rendered test videos: lunges dip 0.30–0.50, split squats ~0.19,
 * marching on the spot at most 0.07. A cycle faster than [minRepMs] is ignored. Only while the torso is fairly
 * upright, so bending over is never counted. Form rule, side-on only: the torso leans more than [maxLean] from
 * vertical in most frames near the lowest point.
 */
class LungeRepCounter(
    private val drop: Double = 0.12,
    private val rise: Double = 0.12,
    private val minRepMs: Long = 700,
    private val maxUprightTilt: Double = 50.0,
    private val maxLean: Double = 30.0,
    private val minVisibility: Float = 0.6f,
    private val smoothingWindow: Int = 3,
    private val minRuleFrames: Int = 3,
    private val ruleFraction: Double = 0.6,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN
    private var standing: Double? = null
    private var peak = 0.0
    private var valley = 0.0
    private var cycleStartMs = 0L
    /** This cycle's frames: hip height, and the torso lean when side-on (null otherwise). Judged when the rep ends,
     *  against the final lowest point — the running lowest point would count the whole descent as "bottom". */
    private val cycle = ArrayList<Pair<Double, Double?>>()
    private val window = ArrayDeque<Double>()

    override val repetitions: Int get() = count

    override fun reset() {
        count = 0
        standing = null
        lose()
    }

    private fun lose() {
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    private fun PoseFrame.seen(vararg l: BodyLandmark) = l.all { this[it].visibility >= minVisibility }

    /** Hip height over torso length, or null when it can't be read or the person is bent over. */
    private fun hipHeight(f: PoseFrame): Double? {
        if (!f.seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val w = f.imageWidth.toDouble(); val h = f.imageHeight.toDouble()
        val sx = (f[BodyLandmark.LEFT_SHOULDER].x + f[BodyLandmark.RIGHT_SHOULDER].x) / 2.0 * w
        val sy = (f[BodyLandmark.LEFT_SHOULDER].y + f[BodyLandmark.RIGHT_SHOULDER].y) / 2.0 * h
        val hx = (f[BodyLandmark.LEFT_HIP].x + f[BodyLandmark.RIGHT_HIP].x) / 2.0 * w
        val hy = (f[BodyLandmark.LEFT_HIP].y + f[BodyLandmark.RIGHT_HIP].y) / 2.0 * h
        val torso = hypot(sx - hx, sy - hy)
        if (torso < 5.0 || hy <= sy) return null
        if (Math.toDegrees(atan2(abs(sx - hx), hy - sy)) > maxUprightTilt) return null
        val ankle = listOf(BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE).filter { f.seen(it) }.maxOfOrNull { f[it].y * h } ?: return null
        return (ankle - hy) / torso
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) hipHeight(frame) else null
        if (raw == null || raw <= 0.0) {
            lose()
            return RepUpdate(count, phase, null)
        }
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val r = window.average()
        val base = maxOf(standing ?: r, r).also { standing = it }
        val x = r / base
        val t = frame.timestampMs
        var event: RepEvent? = null
        when (phase) {
            RepPhase.UNKNOWN -> { phase = RepPhase.TOP; peak = x }
            RepPhase.TOP -> {
                peak = maxOf(peak, x)
                if (x < peak - drop) {
                    phase = RepPhase.BOTTOM; valley = x; cycleStartMs = t; cycle.clear()
                }
            }
            RepPhase.DESCENDING, RepPhase.BOTTOM -> {
                valley = minOf(valley, x)
                cycle.add(x to sideLean(frame))
                if (x > valley + rise) {
                    if (t - cycleStartMs >= minRepMs) {
                        count++
                        val bottom = cycle.filter { it.first <= valley + BOTTOM_BAND }.mapNotNull { it.second }
                        val leaning = bottom.size >= minRuleFrames && bottom.count { it > maxLean } >= ruleFraction * bottom.size
                        event = RepEvent.RepCompleted(count, if (leaning) setOf<FormCue>(LungeIssue.LEANING) else emptySet())
                    }
                    phase = RepPhase.TOP; peak = x
                }
            }
        }
        return RepUpdate(count, phase, x, event)
    }

    /** Torso lean from vertical (degrees) when filmed side-on, else null (the lean can't be read head-on). */
    private fun sideLean(f: PoseFrame): Double? {
        if (!f.seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val w = f.imageWidth.toDouble(); val h = f.imageHeight.toDouble()
        fun d(a: BodyLandmark, b: BodyLandmark) = hypot((f[a].x - f[b].x) * w, (f[a].y - f[b].y) * h)
        val torso = (d(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_HIP) + d(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_HIP)) / 2
        if (torso < 5.0 || d(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER) / torso > 0.45) return null
        val sx = (f[BodyLandmark.LEFT_SHOULDER].x + f[BodyLandmark.RIGHT_SHOULDER].x) / 2.0 * w
        val sy = (f[BodyLandmark.LEFT_SHOULDER].y + f[BodyLandmark.RIGHT_SHOULDER].y) / 2.0 * h
        val hx = (f[BodyLandmark.LEFT_HIP].x + f[BodyLandmark.RIGHT_HIP].x) / 2.0 * w
        val hy = (f[BodyLandmark.LEFT_HIP].y + f[BodyLandmark.RIGHT_HIP].y) / 2.0 * h
        return Math.toDegrees(atan2(abs(sx - hx), hy - sy))
    }

    private companion object {
        /** Frames within this much of the cycle's lowest hip height count as the bottom of the lunge. */
        const val BOTTOM_BAND = 0.05
    }
}
