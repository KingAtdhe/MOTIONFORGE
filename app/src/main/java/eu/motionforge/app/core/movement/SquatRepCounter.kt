package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseGeometry

enum class SquatPhase { UNKNOWN, STANDING, DESCENDING, BOTTOM }

data class RepUpdate(val count: Int, val phase: SquatPhase, val kneeAngle: Double?)

/**
 * Rule-based squat repetition counter (deterministic, explainable, unit-tested).
 *
 * Rule: a repetition is one full cycle  standing → bottom → standing  of the knee angle
 * (hip–knee–ankle, 2D, averaged over the legs that are clearly visible, smoothed over a short
 * window). It only counts depth of the movement cycle — it does NOT judge technique.
 *
 * Thresholds are initial hypotheses to be calibrated with a qualified coach and device tests;
 * they are not biomechanical truths.
 *
 * Safety properties:
 * - Frames passed with tracking = false reset the cycle, so a rep can never be completed
 *   across a tracking gap.
 * - A cycle faster than [minRepMs] is ignored (noise / double count guard).
 */
class SquatRepCounter(
    private val standingAngle: Double = 160.0,
    private val bottomAngle: Double = 115.0,
    private val minVisibility: Float = 0.6f,
    private val minRepMs: Long = 700,
    private val smoothingWindow: Int = 3,
) {
    private var count = 0
    private var phase = SquatPhase.UNKNOWN
    private var cycleStartMs = 0L
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

    fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) kneeAngle(frame) else null
        if (raw == null) {
            loseTracking()
            return RepUpdate(count, phase, null)
        }
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val angle = window.average()

        when (phase) {
            SquatPhase.UNKNOWN -> if (angle >= standingAngle) phase = SquatPhase.STANDING
            SquatPhase.STANDING -> if (angle < standingAngle - DESCENT_MARGIN) {
                phase = SquatPhase.DESCENDING
                cycleStartMs = frame.timestampMs
            }
            SquatPhase.DESCENDING -> when {
                angle <= bottomAngle -> phase = SquatPhase.BOTTOM
                angle >= standingAngle -> phase = SquatPhase.STANDING // shallow dip: not counted
            }
            SquatPhase.BOTTOM -> if (angle >= standingAngle) {
                if (frame.timestampMs - cycleStartMs >= minRepMs) count++
                phase = SquatPhase.STANDING
            }
        }
        return RepUpdate(count, phase, angle)
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
        val SIDES = listOf(
            Triple(BodyLandmark.LEFT_HIP, BodyLandmark.LEFT_KNEE, BodyLandmark.LEFT_ANKLE),
            Triple(BodyLandmark.RIGHT_HIP, BodyLandmark.RIGHT_KNEE, BodyLandmark.RIGHT_ANKLE),
        )
    }
}
