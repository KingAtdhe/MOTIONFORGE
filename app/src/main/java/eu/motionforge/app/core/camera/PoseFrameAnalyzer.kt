package eu.motionforge.app.core.camera

import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import eu.motionforge.app.core.pose.FrameRateLimiter
import eu.motionforge.app.core.pose.MediaPipePoseEngine

/**
 * CameraX analyzer that feeds frames to the pose engine.
 *
 * - Runs on the single-thread analysis executor, never the main thread.
 * - Rate-limited by [FrameRateLimiter].
 * - Every [ImageProxy] is closed in `finally`.
 * - Frames are converted to an in-memory bitmap only; nothing is saved or uploaded.
 * - Rotation is applied so the model sees an upright image. Mirroring is NOT applied:
 *   landmarks stay in true camera coordinates and the overlay mirrors for display.
 */
class PoseFrameAnalyzer(
    private val engine: MediaPipePoseEngine,
    private val previewMirrored: Boolean,
    private val onError: (String) -> Unit,
    targetFps: Int = 15,
) : ImageAnalysis.Analyzer {

    private val limiter = FrameRateLimiter(targetFps)

    override fun analyze(image: ImageProxy) {
        try {
            val now = SystemClock.uptimeMillis()
            if (!limiter.shouldProcess(now)) return
            val upright = image.toBitmap().rotated(image.imageInfo.rotationDegrees)
            engine.submit(upright, now, previewMirrored)
        } catch (e: Exception) {
            // Never let a bad frame kill the analysis thread; report it instead.
            onError(e.message ?: e.javaClass.simpleName)
        } finally {
            image.close()
        }
    }

    private fun Bitmap.rotated(degrees: Int): Bitmap {
        if (degrees == 0) return this
        val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
        val out = Bitmap.createBitmap(this, 0, 0, width, height, matrix, true)
        if (out !== this) recycle()
        return out
    }
}
