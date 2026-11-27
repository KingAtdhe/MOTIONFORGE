package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.PoseFixtures
import eu.motionforge.app.core.pose.PoseFrame
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HoldMonitorTest {

    /** A side-on forearm plank (landscape image): head left, feet right, elbows under the shoulders.
     *  [hipDrop] moves the hips down (positive) or up (negative), in image fractions. */
    private fun plank(t: Long, hipDrop: Float = 0f): PoseFrame {
        val p = mapOf(
            BodyLandmark.NOSE to (0.18f to 0.55f),
            BodyLandmark.LEFT_SHOULDER to (0.25f to 0.60f), BodyLandmark.RIGHT_SHOULDER to (0.25f to 0.60f),
            BodyLandmark.LEFT_ELBOW to (0.25f to 0.75f), BodyLandmark.RIGHT_ELBOW to (0.25f to 0.75f),
            BodyLandmark.LEFT_WRIST to (0.33f to 0.76f), BodyLandmark.RIGHT_WRIST to (0.33f to 0.76f),
            BodyLandmark.LEFT_HIP to (0.50f to 0.63f + hipDrop), BodyLandmark.RIGHT_HIP to (0.50f to 0.63f + hipDrop),
            BodyLandmark.LEFT_KNEE to (0.65f to 0.645f), BodyLandmark.RIGHT_KNEE to (0.65f to 0.645f),
            BodyLandmark.LEFT_ANKLE to (0.80f to 0.66f), BodyLandmark.RIGHT_ANKLE to (0.80f to 0.66f),
            BodyLandmark.LEFT_HEEL to (0.81f to 0.64f), BodyLandmark.RIGHT_HEEL to (0.81f to 0.64f),
            BodyLandmark.LEFT_FOOT_INDEX to (0.82f to 0.69f), BodyLandmark.RIGHT_FOOT_INDEX to (0.82f to 0.69f),
        )
        return PoseFixtures.standingFrame(t, p.mapValues { (_, v) -> PoseFixtures.landmark(v.first, v.second) })
            .copy(imageWidth = 640, imageHeight = 360)
    }

    private fun run(m: HoldMonitor, seconds: Double, start: Long = 0, frame: (Long) -> PoseFrame, tracking: Boolean = true): HoldFeedback {
        var last: HoldFeedback = HoldFeedback.NotAssessing(0)
        var t = start
        while (t < start + (seconds * 1000).toLong()) { last = m.update(frame(t), tracking); t += 66 }
        return last
    }

    @Test
    fun plankHeldIsTimedOnlyWhileInPosition() {
        val m = HoldMonitor(HoldCheck.PLANK)
        val held = run(m, 5.0, frame = { plank(it) })
        assertTrue(held is HoldFeedback.Holding)
        // the first stretch of a second is needed to confirm the position
        assertTrue("held ${held.heldMs}", held.heldMs in 3_800..5_000)
        // standing up stops the timer
        val stood = run(m, 3.0, start = 5_000, frame = { PoseFixtures.standingFrame(it) })
        assertTrue(stood is HoldFeedback.OutOfPosition)
        assertTrue(stood.heldMs <= held.heldMs + 1_000)
    }

    @Test
    fun noTrackingNeverAddsTime() {
        val m = HoldMonitor(HoldCheck.PLANK)
        val r = run(m, 4.0, frame = { plank(it) }, tracking = false)
        assertTrue(r is HoldFeedback.NotAssessing)
        assertEquals(0L, r.heldMs)
    }

    @Test
    fun saggingHipsGetTheLineCue() {
        val m = HoldMonitor(HoldCheck.PLANK)
        val r = run(m, 3.0, frame = { plank(it, hipDrop = 0.10f) })
        assertTrue("$r", r is HoldFeedback.Cue && r.issue == HoldIssue.HIPS_SAG)
        val p = run(HoldMonitor(HoldCheck.PLANK), 3.0, frame = { plank(it, hipDrop = -0.10f) })
        assertTrue("$p", p is HoldFeedback.Cue && p.issue == HoldIssue.HIPS_PIKE)
    }

    @Test
    fun aSingleBadFrameChangesNothing() {
        val m = HoldMonitor(HoldCheck.PLANK)
        run(m, 3.0, frame = { plank(it) })
        val r = m.update(plank(3_000, hipDrop = 0.08f), true)
        assertTrue(r is HoldFeedback.Holding)
    }

    @Test
    fun lessonsWithHoldChecks() {
        assertEquals(HoldCheck.PLANK, HoldCheck.forExercise("forearm_plank"))
        assertEquals(HoldCheck.WALL_SIT, HoldCheck.forExercise("wall_sit"))
        assertNull(HoldCheck.forExercise("bodyweight_squat"))
        assertNull(HoldCheck.forExercise("footwork_lateral"))
        assertEquals(HoldCheck.HAMSTRING, HoldCheck.forExercise("standing_hamstring_stretch"))
        assertEquals(HoldCheck.CALF, HoldCheck.forExercise("standing_calf_stretch"))
        assertEquals(HoldCheck.SQUAT_HOLD, HoldCheck.forExercise("squat_hold"))
        assertNull(HoldCheck.forExercise("standing_quad_stretch"))
    }
}
