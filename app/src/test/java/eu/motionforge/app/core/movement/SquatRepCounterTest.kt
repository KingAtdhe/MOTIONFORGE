package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFixtures
import eu.motionforge.app.core.pose.PoseFrame
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
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
}
