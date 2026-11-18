package eu.motionforge.app.core.pose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FrameRateLimiterTest {

    @Test
    fun firstFrameIsAccepted() {
        assertTrue(FrameRateLimiter(15).shouldProcess(1_000))
    }

    @Test
    fun framesInsideIntervalAreDropped() {
        val limiter = FrameRateLimiter(10) // 100 ms
        assertTrue(limiter.shouldProcess(1_000))
        assertFalse(limiter.shouldProcess(1_050))
        assertTrue(limiter.shouldProcess(1_100))
    }

    @Test
    fun thirtyFpsCameraIsCappedAtTarget() {
        val limiter = FrameRateLimiter(15)
        val accepted = (0 until 30).count { limiter.shouldProcess(10_000L + it * 33L) } // one second of 30 fps
        assertEquals(15, accepted)
    }

    @Test
    fun timestampsMustIncrease() {
        val limiter = FrameRateLimiter(15)
        assertTrue(limiter.shouldProcess(5_000))
        assertFalse(limiter.shouldProcess(4_000))
    }
}
