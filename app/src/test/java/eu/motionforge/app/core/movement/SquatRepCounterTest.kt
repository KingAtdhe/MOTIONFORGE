package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFixtures
import eu.motionforge.app.core.pose.PoseFrame
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin

class SquatRepCounterTest {

    /** Synthetic frame whose both knees have exactly [kneeAngle] degrees (in pixel space, 480x640). */
    private fun frame(kneeAngle: Double, t: Long, kneeVisibility: Float = 0.95f): PoseFrame {
        val a = Math.toRadians((180.0 - kneeAngle) / 2)
        val len = 120.0
        fun leg(hipX: Double): Map<BodyLandmark, Landmark> {
            val hip = hipX to 300.0
            val knee = (hip.first + len * sin(a)) to (hip.second + len * cos(a))
            val ankle = (knee.first - len * sin(a)) to (knee.second + len * cos(a))
            fun lm(p: Pair<Double, Double>, v: Float) = PoseFixtures.landmark((p.first / 480).toFloat(), (p.second / 640).toFloat(), v)
            return mapOf(0 to lm(hip, 0.95f), 1 to lm(knee, kneeVisibility), 2 to lm(ankle, 0.95f)).let { m ->
                val left = hipX > 240
                mapOf(
                    (if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP) to m.getValue(0),
                    (if (left) BodyLandmark.LEFT_KNEE else BodyLandmark.RIGHT_KNEE) to m.getValue(1),
                    (if (left) BodyLandmark.LEFT_ANKLE else BodyLandmark.RIGHT_ANKLE) to m.getValue(2),
                )
            }
        }
        return PoseFixtures.standingFrame(t, leg(270.0) + leg(210.0))
    }

    /** Feeds a sequence of angles at 15 fps; returns the final count. */
    private fun SquatRepCounter.feed(angles: List<Double>, startMs: Long = 0, tracking: Boolean = true): Long {
        var t = startMs
        angles.forEach { update(frame(it, t), tracking); t += 66 }
        return t
    }

    private fun cycle(bottom: Double, framesEachWay: Int = 12): List<Double> {
        val down = (0..framesEachWay).map { 175.0 - (175.0 - bottom) * it / framesEachWay }
        return List(4) { 175.0 } + down + List(3) { bottom } + down.reversed() + List(4) { 175.0 }
    }

    @Test
    fun fullCycleCountsOnce() {
        val c = SquatRepCounter()
        c.feed(cycle(95.0))
        assertEquals(1, c.repetitions)
    }

    @Test
    fun threeCyclesCountThree() {
        val c = SquatRepCounter()
        var t = 0L
        repeat(3) { t = c.feed(cycle(95.0), t) }
        assertEquals(3, c.repetitions)
    }

    @Test
    fun shallowDipIsNotCounted() {
        val c = SquatRepCounter()
        c.feed(cycle(140.0))
        assertEquals(0, c.repetitions)
    }

    @Test
    fun jitterAtTheBottomDoesNotDoubleCount() {
        val c = SquatRepCounter()
        val down = (0..12).map { 175.0 - 80.0 * it / 12 }
        c.feed(List(4) { 175.0 } + down + listOf(95.0, 118.0, 96.0, 119.0, 95.0, 117.0, 95.0) + down.reversed() + List(4) { 175.0 })
        assertEquals(1, c.repetitions)
    }

    @Test
    fun impossiblyFastCycleIsIgnored() {
        val c = SquatRepCounter(smoothingWindow = 1)
        c.feed(listOf(175.0, 175.0, 140.0, 100.0, 140.0, 175.0, 175.0)) // ~260 ms
        assertEquals(0, c.repetitions)
    }

    @Test
    fun trackingLossMidRepDiscardsThatRep() {
        val c = SquatRepCounter()
        val down = (0..12).map { 175.0 - 80.0 * it / 12 }
        var t = c.feed(List(4) { 175.0 } + down)
        t = c.feed(listOf(95.0, 95.0), t, tracking = false)
        c.feed(down.reversed() + List(4) { 175.0 }, t)
        assertEquals(0, c.repetitions)
    }

    @Test
    fun hiddenKneesGiveNoAngle() {
        val c = SquatRepCounter()
        val u = c.update(frame(95.0, 0, kneeVisibility = 0.2f), tracking = true)
        assertNull(u.kneeAngle)
        assertEquals(SquatPhase.UNKNOWN, u.phase)
    }

    @Test
    fun mustSeeStandingBeforeCounting() {
        // Starting already at the bottom: rising alone is not a repetition.
        val c = SquatRepCounter()
        c.feed(List(5) { 95.0 } + (0..12).map { 95.0 + 80.0 * it / 12 } + List(4) { 175.0 })
        assertEquals(0, c.repetitions)
    }

    /** Collects the form events while feeding angles (frames built by [make]). */
    private fun SquatRepCounter.events(angles: List<Double>, msPerFrame: Long = 66, make: (Double, Long) -> PoseFrame = { a, t -> frame(a, t) }): List<SquatEvent> {
        var t = 0L
        return angles.mapNotNull { a -> update(make(a, t), true).event.also { t += msPerFrame } }
    }

    private fun slowCycle(bottom: Double) = cycle(bottom, framesEachWay = 24)

    @Test
    fun controlledRepHasNoIssues() {
        val ev = SquatRepCounter().events(slowCycle(95.0))
        assertEquals(listOf(SquatEvent.RepCompleted(1, emptySet())), ev)
    }

    @Test
    fun droppingIntoTheBottomIsRushed() {
        val ev = SquatRepCounter().events(cycle(95.0, framesEachWay = 5))
        assertEquals(listOf(SquatEvent.RepCompleted(1, setOf(SquatIssue.RUSHED))), ev)
    }

    @Test
    fun clearShallowAttemptIsReported() {
        val ev = SquatRepCounter().events(slowCycle(125.0))
        assertEquals(listOf(SquatEvent.ShallowRep), ev)
    }

    @Test
    fun smallDipIsNotReportedAsAnAttempt() {
        assertTrue(SquatRepCounter().events(slowCycle(145.0)).isEmpty())
    }

    /** Front view with both knees bending toward the midline (knees closer together than the ankles). */
    private fun kneesInFrame(kneeAngle: Double, t: Long): PoseFrame {
        val a = Math.toRadians((180.0 - kneeAngle) / 2)
        val len = 120.0
        fun leg(hipX: Double, dir: Double, hip: BodyLandmark, knee: BodyLandmark, ankle: BodyLandmark): Map<BodyLandmark, Landmark> {
            val kx = hipX + dir * len * sin(a); val ky = 300.0 + len * cos(a)
            fun lm(x: Double, y: Double) = PoseFixtures.landmark((x / 480).toFloat(), (y / 640).toFloat())
            return mapOf(hip to lm(hipX, 300.0), knee to lm(kx, ky), ankle to lm(hipX, ky + len * cos(a)))
        }
        return PoseFixtures.standingFrame(
            t,
            leg(330.0, -1.0, BodyLandmark.LEFT_HIP, BodyLandmark.LEFT_KNEE, BodyLandmark.LEFT_ANKLE) +
                leg(150.0, 1.0, BodyLandmark.RIGHT_HIP, BodyLandmark.RIGHT_KNEE, BodyLandmark.RIGHT_ANKLE),
        )
    }

    @Test
    fun kneesCavingAtTheBottomSeenFromTheFront() {
        val ev = SquatRepCounter().events(slowCycle(95.0)) { a, t -> kneesInFrame(a, t) }
        val rep = ev.single() as SquatEvent.RepCompleted
        assertEquals(setOf(SquatIssue.KNEES_IN), rep.issues)
    }

    @Test
    fun chestDroppingSeenFromTheSide() {
        // side view: shoulders overlap in the image, and at the bottom they sit far forward of the hips (~70 deg lean)
        val ev = SquatRepCounter().events(slowCycle(95.0)) { a, t ->
            val f = frame(a, t)
            val fixed = f.landmarks.toMutableList()
            // hips stay where frame() put them (mid x = 240 px, y = 300 px); bottom: 165 px forward, 60 px up = ~70 deg
            val sy = if (a > 115.0) 0.25f else 0.375f
            val sx = if (a > 115.0) 0.50f else 0.50f + 165f / 480f
            fixed[BodyLandmark.LEFT_SHOULDER.index] = PoseFixtures.landmark(sx + 0.01f, sy)
            fixed[BodyLandmark.RIGHT_SHOULDER.index] = PoseFixtures.landmark(sx - 0.01f, sy)
            f.copy(landmarks = fixed)
        }
        val rep = ev.single() as SquatEvent.RepCompleted
        assertTrue(rep.toString(), SquatIssue.CHEST_DROP in rep.issues)
        assertTrue(SquatIssue.KNEES_IN !in rep.issues)
    }
}
