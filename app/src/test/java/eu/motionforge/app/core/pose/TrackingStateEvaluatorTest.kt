package eu.motionforge.app.core.pose

import eu.motionforge.app.core.pose.PoseFixtures.detected
import eu.motionforge.app.core.pose.PoseFixtures.landmark
import eu.motionforge.app.core.pose.PoseFixtures.standingFrame
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TrackingStateEvaluatorTest {

    private fun evaluator(stable: Int = 5) = TrackingStateEvaluator(TrackingStateEvaluator.FULL_BODY, stableFramesRequired = stable)

    @Test
    fun noPersonAsksUserToMoveIntoView() {
        assertEquals(TrackingState.MOVE_INTO_VIEW, evaluator().update(PoseOutput.NoPerson(0, 20)))
    }

    @Test
    fun singleGoodFrameNeverUnlocksTracking() {
        val e = evaluator()
        val state = e.update(detected(standingFrame()))
        assertEquals(TrackingState.CALIBRATING, state)
        assertFalse(state.allowsFeedback)
    }

    @Test
    fun trackingOnlyAfterConsecutiveGoodFrames() {
        val e = evaluator(stable = 5)
        repeat(4) { assertEquals(TrackingState.CALIBRATING, e.update(detected(standingFrame(it.toLong())))) }
        val fifth = e.update(detected(standingFrame(5)))
        assertEquals(TrackingState.TRACKING, fifth)
        assertTrue(fifth.allowsFeedback)
    }

    @Test
    fun badFrameResetsTheStreak() {
        val e = evaluator(stable = 3)
        repeat(3) { e.update(detected(standingFrame(it.toLong()))) }
        assertEquals(TrackingState.TRACKING, e.update(detected(standingFrame(3))))
        e.update(PoseOutput.NoPerson(4, 20))
        assertEquals(0, e.consecutiveGoodFrames)
        assertEquals(TrackingState.CALIBRATING, e.update(detected(standingFrame(5))))
    }

    @Test
    fun anklesOutOfFrameAskToAdjustCamera() {
        val frame = standingFrame(overrides = mapOf(
            BodyLandmark.LEFT_ANKLE to landmark(0.55f, 1.04f),
            BodyLandmark.RIGHT_ANKLE to landmark(0.45f, 1.04f),
        ))
        assertEquals(TrackingState.ADJUST_CAMERA, evaluator().update(detected(frame)))
    }

    @Test
    fun landmarkTouchingEdgeCountsAsOutOfFrame() {
        val frame = standingFrame(overrides = mapOf(BodyLandmark.LEFT_ANKLE to landmark(0.55f, 0.995f)))
        assertEquals(TrackingState.ADJUST_CAMERA, evaluator().update(detected(frame)))
    }

    @Test
    fun overallLowVisibilityIsLowConfidence() {
        val low = TrackingStateEvaluator.FULL_BODY.associateWith { lm ->
            val f = standingFrame()[lm]
            f.copy(visibility = 0.3f)
        }
        assertEquals(TrackingState.LOW_CONFIDENCE, evaluator().update(detected(standingFrame(overrides = low))))
    }

    @Test
    fun oneHiddenJointIsOccluded() {
        val frame = standingFrame()
        val hidden = mapOf(BodyLandmark.LEFT_KNEE to frame[BodyLandmark.LEFT_KNEE].copy(visibility = 0.2f))
        assertEquals(TrackingState.OCCLUDED, evaluator().update(detected(standingFrame(overrides = hidden))))
    }

    @Test
    fun pipelineErrorIsCameraError() {
        assertEquals(TrackingState.CAMERA_ERROR, evaluator().update(PoseOutput.Error("boom")))
    }

    @Test
    fun onlyTrackingAllowsFeedback() {
        TrackingState.entries.forEach { s ->
            assertEquals("allowsFeedback for $s", s == TrackingState.TRACKING, s.allowsFeedback)
        }
    }

    @Test(expected = IllegalArgumentException::class)
    fun singleFrameStabilityIsRejected() {
        TrackingStateEvaluator(TrackingStateEvaluator.FULL_BODY, stableFramesRequired = 1)
    }
}
