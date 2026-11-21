package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFixtures
import eu.motionforge.app.core.pose.PoseFrame
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BoxingFormMonitorTest {

    private fun lm(x: Float, y: Float, v: Float = 0.95f) = PoseFixtures.landmark(x, y, v)

    /** Guard: wrists at chin height in front of the shoulders; feet ~1.25 shoulder widths apart. */
    private fun guard(t: Long, extra: Map<BodyLandmark, Landmark> = emptyMap()): PoseFrame = PoseFixtures.standingFrame(
        t,
        mapOf(
            BodyLandmark.LEFT_ELBOW to lm(0.60f, 0.30f), BodyLandmark.RIGHT_ELBOW to lm(0.40f, 0.30f),
            BodyLandmark.LEFT_WRIST to lm(0.54f, 0.17f), BodyLandmark.RIGHT_WRIST to lm(0.46f, 0.17f),
            BodyLandmark.LEFT_ANKLE to lm(0.62f, 0.88f), BodyLandmark.RIGHT_ANKLE to lm(0.38f, 0.88f),
        ) + extra,
    )

    private fun BoxingFormMonitor.feed(n: Int, start: Long, make: (Long) -> PoseFrame, tracking: Boolean = true): Pair<FormFeedback, Long> {
        var t = start
        var last: FormFeedback = FormFeedback.Steady(0)
        repeat(n) { last = update(make(t), tracking); t += 66 }
        return last to t
    }

    @Test
    fun goodGuardGivesNoCue() {
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        val (fb, _) = m.feed(45, 0, { guard(it) })
        assertTrue(fb is FormFeedback.Steady)
    }

    @Test
    fun handsLowForASecondGivesTheHandsCue() {
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        val (fb, _) = m.feed(30, 0, { PoseFixtures.standingFrame(it, mapOf(BodyLandmark.LEFT_ANKLE to lm(0.62f, 0.88f), BodyLandmark.RIGHT_ANKLE to lm(0.38f, 0.88f))) })
        assertEquals(FormFeedback.Cue(FormIssue.HANDS_LOW, 0), fb)
    }

    @Test
    fun aSingleBadFrameNeverGivesAdvice() {
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        var (_, t) = m.feed(20, 0, { guard(it) })
        m.update(PoseFixtures.standingFrame(t), tracking = true); t += 66
        val (fb, _) = m.feed(3, t, { guard(it) })
        assertTrue(fb is FormFeedback.Steady)
    }

    @Test
    fun bladedStanceSeenFromTheDiagonalIsNotCalledNarrow() {
        // shoulders turned away from the camera (narrow in the image) and the feet lined up behind each other:
        // the spacing cannot be read from this angle, so there must be no feet cue
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        val turned = mapOf(
            BodyLandmark.LEFT_SHOULDER to lm(0.53f, 0.25f), BodyLandmark.RIGHT_SHOULDER to lm(0.47f, 0.25f),
            BodyLandmark.LEFT_ELBOW to lm(0.54f, 0.30f), BodyLandmark.RIGHT_ELBOW to lm(0.46f, 0.30f),
            BodyLandmark.LEFT_WRIST to lm(0.53f, 0.17f), BodyLandmark.RIGHT_WRIST to lm(0.47f, 0.17f),
            BodyLandmark.LEFT_ANKLE to lm(0.52f, 0.88f), BodyLandmark.RIGHT_ANKLE to lm(0.48f, 0.88f),
        )
        val (fb, _) = m.feed(30, 0, { guard(it, turned) })
        assertTrue("got $fb", fb is FormFeedback.Steady)
    }

    @Test
    fun narrowFeetAreFlagged() {
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        val (fb, _) = m.feed(30, 0, { guard(it, mapOf(BodyLandmark.LEFT_ANKLE to lm(0.52f, 0.88f), BodyLandmark.RIGHT_ANKLE to lm(0.48f, 0.88f))) })
        assertEquals(FormFeedback.Cue(FormIssue.FEET_NARROW, 0), fb)
    }

    @Test
    fun lowVisibilityMeansNotAssessing() {
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        val (fb, _) = m.feed(30, 0, { guard(it, mapOf(BodyLandmark.LEFT_WRIST to lm(0.54f, 0.17f, v = 0.2f))) })
        assertTrue(fb is FormFeedback.NotAssessing)
    }

    @Test
    fun trackingOffMeansNotAssessing() {
        val m = BoxingFormMonitor(BoxingDrill.STANCE)
        val (fb, _) = m.feed(30, 0, { guard(it) }, tracking = false)
        assertTrue(fb is FormFeedback.NotAssessing)
    }

    /** Lead (left) arm straight out to the side of the image at shoulder height. */
    private fun jabOut(t: Long, rearLow: Boolean = false) = guard(
        t,
        mapOf(BodyLandmark.LEFT_ELBOW to lm(0.70f, 0.25f), BodyLandmark.LEFT_WRIST to lm(0.82f, 0.25f)) +
            (if (rearLow) mapOf(BodyLandmark.RIGHT_WRIST to lm(0.42f, 0.45f), BodyLandmark.RIGHT_ELBOW to lm(0.40f, 0.36f)) else emptyMap()),
    )

    @Test
    fun jabsAreCountedOncePerExtension() {
        val m = BoxingFormMonitor(BoxingDrill.JAB)
        var t = 0L
        repeat(3) {
            t = m.feed(8, t, { guard(it) }).second
            t = m.feed(5, t, { jabOut(it) }).second
        }
        t = m.feed(8, t, { guard(it) }).second
        assertEquals(3, m.jabs)
    }

    @Test
    fun rearHandDroppingDuringTheJabIsFlagged() {
        val m = BoxingFormMonitor(BoxingDrill.JAB)
        var t = m.feed(10, 0, { guard(it) }).second
        val (fb, _) = m.feed(16, t, { jabOut(it, rearLow = true) })
        assertEquals(FormIssue.REAR_HAND_DROPS, (fb as FormFeedback.Cue).issue)
    }

    @Test
    fun holdingTheJabOutAsksForTheReturn() {
        val m = BoxingFormMonitor(BoxingDrill.JAB)
        val t = m.feed(10, 0, { guard(it) }).second
        val (fb, _) = m.feed(45, t, { jabOut(it) })
        assertEquals(FormIssue.SLOW_RETURN, (fb as FormFeedback.Cue).issue)
    }
}
