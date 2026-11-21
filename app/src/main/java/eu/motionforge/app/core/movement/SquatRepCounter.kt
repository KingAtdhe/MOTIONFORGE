package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseGeometry
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot

enum class SquatPhase { UNKNOWN, STANDING, DESCENDING, BOTTOM }

/**
 * Possible form adjustments the squat check can name for one repetition. Each is a simple 2D rule; the
 * wording is a suggestion, never a judgement of safety or injury risk.
 * [message] is shown on screen, [spoken] is the short version the voice coach says.
 */
enum class SquatIssue(val message: String, val spoken: String) {
    RUSHED("Possible form adjustment: slow down and control the way down.", "Slow down on the way down."),
    KNEES_IN("Possible form adjustment: let your knees travel in line with your toes.", "Knees in line with your toes."),
    CHEST_DROP("Possible form adjustment: keep your chest a little more upright.", "Chest up a little."),
}

/** Something worth telling the person about, produced once at the end of a movement cycle. */
sealed interface SquatEvent {
    /** A counted repetition; [issues] empty means no rule found anything to adjust. */
    data class RepCompleted(val rep: Int, val issues: Set<SquatIssue>) : SquatEvent

    /** A clear dip that did not reach counting depth and was not counted. */
    data object ShallowRep : SquatEvent
}

data class RepUpdate(val count: Int, val phase: SquatPhase, val kneeAngle: Double?, val event: SquatEvent? = null)

/**
 * Rule-based squat repetition counter with per-repetition form checks (deterministic, explainable, unit-tested).
 *
 * Counting rule: a repetition is one full cycle  standing → bottom → standing  of the knee angle
 * (hip–knee–ankle, 2D, averaged over the legs that are clearly visible, smoothed over a short window).
 *
 * Form rules, evaluated over the frames of each cycle and reported once when it ends:
 * - [SquatIssue.RUSHED]: the way down took less than [minDescentMs].
 * - [SquatIssue.KNEES_IN]: camera roughly in front, and at the bottom the knees are clearly closer together
 *   than the ankles (ratio below [kneesInRatio]) in most bottom frames.
 * - [SquatIssue.CHEST_DROP]: camera roughly from the side, and at the bottom the hip→shoulder line leans more than
 *   [maxLeanDegrees] from vertical in most bottom frames.
 * - Shallow: a dip below [shallowAngle] that turns back before [bottomAngle] (not counted).
 * Front/side is decided per frame from the shoulder width relative to the torso length; rules that need the other
 * view are simply not evaluated, so a side-on person never gets a knees cue and vice versa.
 *
 * Thresholds are initial hypotheses to be calibrated with a qualified coach and device tests;
 * they are not biomechanical truths.
 *
 * Safety properties:
 * - Frames passed with tracking = false reset the cycle, so a rep can never be completed
 *   across a tracking gap, and no form event is produced from it.
 * - A cycle faster than [minRepMs] is ignored (noise / double count guard).
 * - A form rule needs at least [minRuleFrames] qualifying bottom frames; one bad frame never produces a cue.
 */
class SquatRepCounter(
    private val standingAngle: Double = 160.0,
    private val bottomAngle: Double = 115.0,
    private val minVisibility: Float = 0.6f,
    private val minRepMs: Long = 700,
    private val smoothingWindow: Int = 3,
    private val minDescentMs: Long = 550,
    private val kneesInRatio: Double = 0.75,
    private val maxLeanDegrees: Double = 60.0,
    private val shallowAngle: Double = 135.0,
    private val frontalRatio: Double = 0.40,
    private val minRuleFrames: Int = 3,
    private val ruleFraction: Double = 0.6,
) {
    private var count = 0
    private var phase = SquatPhase.UNKNOWN
    private var cycleStartMs = 0L
    private var bottomAtMs = 0L
    private var minAngle = 180.0
    private var frontalBottom = 0
    private var kneesInBottom = 0
    private var sideBottom = 0
    private var leanBottom = 0
    private val window = ArrayDeque<Double>()

    val repetitions: Int get() = count

    fun reset() {
        count = 0
        loseTracking()
    }

    private fun loseTracking() {
        phase = SquatPhase.UNKNOWN
        window.clear()
    }

    private fun startCycle(t: Long) {
        cycleStartMs = t
        bottomAtMs = 0L
        minAngle = 180.0
        frontalBottom = 0; kneesInBottom = 0; sideBottom = 0; leanBottom = 0
    }

    fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) kneeAngle(frame) else null
        if (raw == null) {
            loseTracking()
            return RepUpdate(count, phase, null)
        }
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val angle = window.average()
        val t = frame.timestampMs
        var event: SquatEvent? = null

        if (phase == SquatPhase.DESCENDING || phase == SquatPhase.BOTTOM) minAngle = minOf(minAngle, angle)
        when (phase) {
            SquatPhase.UNKNOWN -> if (angle >= standingAngle) phase = SquatPhase.STANDING
            SquatPhase.STANDING -> if (angle < standingAngle - DESCENT_MARGIN) {
                phase = SquatPhase.DESCENDING
                startCycle(t)
                minAngle = angle
            }
            SquatPhase.DESCENDING -> when {
                angle <= bottomAngle -> { phase = SquatPhase.BOTTOM; bottomAtMs = t }
                angle >= standingAngle -> {
                    // shallow dip: not counted; said only when it was clearly an attempt
                    if (minAngle <= shallowAngle) event = SquatEvent.ShallowRep
                    phase = SquatPhase.STANDING
                }
            }
            SquatPhase.BOTTOM -> if (angle >= standingAngle) {
                if (t - cycleStartMs >= minRepMs) {
                    count++
                    event = SquatEvent.RepCompleted(count, issuesOfCycle())
                }
                phase = SquatPhase.STANDING
            }
        }
        // the form rules look at the deepest part only (the phase stays BOTTOM until standing again)
        if (phase == SquatPhase.BOTTOM && angle <= bottomAngle + BOTTOM_BAND) observeBottom(frame)
        return RepUpdate(count, phase, angle, event)
    }

    private fun issuesOfCycle(): Set<SquatIssue> = buildSet {
        if (bottomAtMs > 0 && bottomAtMs - cycleStartMs < minDescentMs) add(SquatIssue.RUSHED)
        if (frontalBottom >= minRuleFrames && kneesInBottom >= ruleFraction * frontalBottom) add(SquatIssue.KNEES_IN)
        if (sideBottom >= minRuleFrames && leanBottom >= ruleFraction * sideBottom) add(SquatIssue.CHEST_DROP)
    }

    /** Collects the per-frame form measurements while the person is at the bottom of the squat. */
    private fun observeBottom(f: PoseFrame) {
        val w = f.imageWidth.toDouble()
        val h = f.imageHeight.toDouble()
        fun ok(vararg l: BodyLandmark) = l.all { f[it].visibility >= minVisibility }
        fun d(a: Landmark, b: Landmark) = hypot((a.x - b.x) * w, (a.y - b.y) * h)
        if (!ok(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return
        val ls = f[BodyLandmark.LEFT_SHOULDER]; val rs = f[BodyLandmark.RIGHT_SHOULDER]
        val lh = f[BodyLandmark.LEFT_HIP]; val rh = f[BodyLandmark.RIGHT_HIP]
        val torso = (d(ls, lh) + d(rs, rh)) / 2
        if (torso < 10.0) return
        val frontal = d(ls, rs) / torso >= frontalRatio
        if (frontal) {
            if (!ok(BodyLandmark.LEFT_KNEE, BodyLandmark.RIGHT_KNEE, BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE)) return
            val ankles = abs((f[BodyLandmark.LEFT_ANKLE].x - f[BodyLandmark.RIGHT_ANKLE].x) * w)
            if (ankles < 10.0) return
            val knees = abs((f[BodyLandmark.LEFT_KNEE].x - f[BodyLandmark.RIGHT_KNEE].x) * w)
            frontalBottom++
            if (knees / ankles < kneesInRatio) kneesInBottom++
        } else {
            // hip -> shoulder direction against image vertical (y grows downward)
            val dx = ((ls.x + rs.x) / 2 - (lh.x + rh.x) / 2) * w
            val dy = ((lh.y + rh.y) / 2 - (ls.y + rs.y) / 2) * h
            val lean = Math.toDegrees(atan2(abs(dx), dy))
            sideBottom++
            if (lean > maxLeanDegrees) leanBottom++
        }
    }

    private fun kneeAngle(frame: PoseFrame): Double? {
        val angles = SIDES.mapNotNull { (hip, knee, ankle) ->
            val h = frame[hip]; val k = frame[knee]; val a = frame[ankle]
            if (h.visibility < minVisibility || k.visibility < minVisibility || a.visibility < minVisibility) {
                null
            } else {
                PoseGeometry.angleDegrees2d(h, k, a, frame.imageWidth, frame.imageHeight)
            }
        }
        return if (angles.isEmpty()) null else angles.average()
    }

    private companion object {
        const val DESCENT_MARGIN = 10.0
        const val BOTTOM_BAND = 8.0
        val SIDES = listOf(
            Triple(BodyLandmark.LEFT_HIP, BodyLandmark.LEFT_KNEE, BodyLandmark.LEFT_ANKLE),
            Triple(BodyLandmark.RIGHT_HIP, BodyLandmark.RIGHT_KNEE, BodyLandmark.RIGHT_ANKLE),
        )
    }
}
