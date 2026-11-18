package eu.motionforge.app.core.pose

/**
 * Decides whether a camera frame should be sent to the pose model, to cap inference at
 * [targetFps] (initial target 15 fps; measure on mid-range devices and adjust).
 * Timestamps must be monotonic (e.g. SystemClock.uptimeMillis()).
 */
class FrameRateLimiter(targetFps: Int) {
    init {
        require(targetFps in 1..60) { "targetFps must be 1..60" }
    }

    private val minIntervalMs: Long = 1000L / targetFps
    private var lastAcceptedMs: Long = Long.MIN_VALUE

    fun shouldProcess(nowMs: Long): Boolean {
        if (lastAcceptedMs != Long.MIN_VALUE && nowMs - lastAcceptedMs < minIntervalMs) return false
        // MediaPipe LIVE_STREAM requires strictly increasing timestamps.
        if (lastAcceptedMs != Long.MIN_VALUE && nowMs <= lastAcceptedMs) return false
        lastAcceptedMs = nowMs
        return true
    }
}
