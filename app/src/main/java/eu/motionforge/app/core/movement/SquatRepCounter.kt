package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseGeometry
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot


/**
 * Possible form adjustments the squat check can name for one repetition. Each is a simple 2D rule; the
 * wording is a suggestion, never a judgement of safety or injury risk.
 * [message] is shown on screen, [spoken] is the short version the voice coach says.
 */
enum class SquatIssue(override val message: String, override val spoken: String) : FormCue {
    RUSHED("Possible form adjustment: slow down and control the way down.", "Slow down on the way down."),
    KNEES_IN("Possible form adjustment: let your knees travel in line with your toes.", "Knees in line with your toes."),
    CHEST_DROP("Possible form adjustment: keep your chest a little more upright.", "Chest up a little."),
}


/**
 * Rule-based squat repetition counter with per-repetition form checks (deterministic, explainable, unit-tested).
 *
 * Counting rule: a repetition is one full cycle  standing → bottom → standing  of the knee angle
 * (hip–knee–ankle, 2D, averaged over the legs that are clearly visible, smoothed over a short window).
 * Filmed from the front, a knee that bends toward the camera looks straight in a 2D image (knees caving in, or
 * pointing straight at the phone): on rendered test videos the 2D angle stayed ~170° at full depth. So the angle
 * used is the smaller of the 2D knee angle and an equivalent angle from how far the hips have dropped (hip→lower
 * ankle height over torso length, against the standing value): 180 − 220·(1 − ratio).
 *
 * Form rules, evaluated over the frames of each cycle and reported once when it ends:
 * - [SquatIssue.RUSHED]: the way down, from leaving the top to the deepest point, took less than [minDescentMs]
 *   (a drop rather than a lowering). Timed to the deepest point, not to counting depth: the middle of even a slow
 *   descent passes counting depth quickly, which flagged controlled squats on the rendered test videos.
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
 * - Frames passed with tracking = false for more than half a second reset the cycle, so a rep can never be
 *   completed across a tracking gap; a shorter blip (one missed frame and the tracking gate re-settling) is skipped.
 * - A cycle faster than [minRepMs] is ignored (noise / double count guard).
 * - A form rule needs at least [minRuleFrames] qualifying bottom frames; one bad frame never produces a cue.
 */
class SquatRepCounter(
    private val standingAngle: Double = 160.0,
    private val bottomAngle: Double = 115.0,
    private val minVisibility: Float = 0.6f,
    private val minRepMs: Long = 700,
    private val smoothingWindow: Int = 3,
    private val minDescentMs: Long = 500,
    private val kneesInRatio: Double = 0.90,
    private val maxLeanDegrees: Double = 60.0,
    private val shallowAngle: Double = 135.0,
    private val frontalRatio: Double = 0.40,
    private val minRuleFrames: Int = 3,
    private val ruleFraction: Double = 0.6,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN
    private var cycleStartMs = 0L
    private var bottomAtMs = 0L
    private var deepestAtMs = 0L
    private var minAngle = 180.0
    private var frontalBottom = 0
    private var kneesInBottom = 0
    private var sideBottom = 0
    private var leanBottom = 0
    private val window = ArrayDeque<Double>()
    private var standingHip: Double? = null
    private var lastGoodMs = -1L

    override val repetitions: Int get() = count

    override fun reset() {
        count = 0
        standingHip = null
        loseTracking()
    }

    private fun loseTracking() {
        lastGoodMs = -1L
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    private fun startCycle(t: Long) {
        cycleStartMs = t
        bottomAtMs = 0L
        deepestAtMs = t
        minAngle = 180.0
        frontalBottom = 0; kneesInBottom = 0; sideBottom = 0; leanBottom = 0
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) kneeAngle(frame) else null
        if (raw == null) {
            // a blip of a few frames (the model missing one frame, then the tracking gate re-settling) keeps the
            // rep in progress; a longer gap drops it, so a rep can never span a real loss of tracking
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, phase, null)
            loseTracking()
            return RepUpdate(count, phase, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val angle = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null

        if ((phase == RepPhase.DESCENDING || phase == RepPhase.BOTTOM) && angle < minAngle) {
            minAngle = angle
            deepestAtMs = t
        }
        when (phase) {
            RepPhase.UNKNOWN -> if (angle >= standingAngle) phase = RepPhase.TOP
            RepPhase.TOP -> if (angle < standingAngle - DESCENT_MARGIN) {
                phase = RepPhase.DESCENDING
                startCycle(t)
                minAngle = angle
            }
            RepPhase.DESCENDING -> when {
                angle <= bottomAngle -> { phase = RepPhase.BOTTOM; bottomAtMs = t }
                angle >= standingAngle -> {
                    // shallow dip: not counted; said only when it was clearly an attempt
                    if (minAngle <= shallowAngle) event = RepEvent.ShallowRep
                    phase = RepPhase.TOP
                }
            }
            RepPhase.BOTTOM -> if (angle >= standingAngle) {
                if (t - cycleStartMs >= minRepMs) {
                    count++
                    event = RepEvent.RepCompleted(count, issuesOfCycle())
                }
                phase = RepPhase.TOP
            }
        }
        // the form rules look at the deepest part only (the phase stays BOTTOM until standing again)
        if (phase == RepPhase.BOTTOM && angle <= bottomAngle + BOTTOM_BAND) observeBottom(frame)
        return RepUpdate(count, phase, angle, event)
    }

    private fun issuesOfCycle(): Set<FormCue> = buildSet {
        if (bottomAtMs > 0 && deepestAtMs - cycleStartMs < minDescentMs) add(SquatIssue.RUSHED)
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

    /** Hip height (hips → lower visible ankle, over torso length) as an equivalent knee angle, or null. */
    private fun hipDropAngle(f: PoseFrame): Double? {
        val torsoLms = listOf(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)
        if (torsoLms.any { f[it].visibility < minVisibility }) return null
        val w = f.imageWidth.toDouble(); val h = f.imageHeight.toDouble()
        val sx = (f[BodyLandmark.LEFT_SHOULDER].x + f[BodyLandmark.RIGHT_SHOULDER].x) / 2.0 * w
        val sy = (f[BodyLandmark.LEFT_SHOULDER].y + f[BodyLandmark.RIGHT_SHOULDER].y) / 2.0 * h
        val hx = (f[BodyLandmark.LEFT_HIP].x + f[BodyLandmark.RIGHT_HIP].x) / 2.0 * w
        val hy = (f[BodyLandmark.LEFT_HIP].y + f[BodyLandmark.RIGHT_HIP].y) / 2.0 * h
        val torso = hypot(sx - hx, sy - hy)
        if (torso < 5.0) return null
        val ankle = listOf(BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE).filter { f[it].visibility >= minVisibility }
            .maxOfOrNull { f[it].y * h } ?: return null
        val r = (ankle - hy) / torso
        if (r <= 0.0) return null
        val base = maxOf(standingHip ?: r, r).also { standingHip = it }
        return 180.0 - 220.0 * (1.0 - r / base)
    }

    private fun kneeAngle(frame: PoseFrame): Double? {
        val knee = kneeAngle2d(frame)
        val drop = hipDropAngle(frame)
        return when {
            knee == null -> null                     // the legs must be seen: the hip drop alone is not a squat check
            drop == null -> knee
            else -> minOf(knee, drop)
        }
    }

    private fun kneeAngle2d(frame: PoseFrame): Double? {
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
