package eu.motionforge.app.core.pose

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarkerResult
import java.util.concurrent.ConcurrentHashMap

/**
 * Wraps MediaPipe Pose Landmarker (LIVE_STREAM mode). This is the only class that touches
 * MediaPipe types; results are converted to [PoseOutput] before leaving.
 *
 * Frames are handled in memory only. Nothing is written to disk or sent anywhere.
 */
class MediaPipePoseEngine private constructor(
    private val landmarker: PoseLandmarker,
    private val pending: ConcurrentHashMap<Long, PendingFrame>,
) : AutoCloseable {

    internal data class PendingFrame(
        val submittedAtMs: Long,
        val width: Int,
        val height: Int,
        val previewMirrored: Boolean,
    )

    /**
     * Submits an upright (already rotated) bitmap. [timestampMs] must strictly increase.
     * Results arrive on the listener passed to [create], on a MediaPipe thread.
     */
    fun submit(uprightBitmap: Bitmap, timestampMs: Long, previewMirrored: Boolean) {
        pending[timestampMs] = PendingFrame(
            submittedAtMs = SystemClock.uptimeMillis(),
            width = uprightBitmap.width,
            height = uprightBitmap.height,
            previewMirrored = previewMirrored,
        )
        // Guard against unbounded growth if the model drops frames without a callback.
        if (pending.size > MAX_PENDING) {
            pending.keys.sorted().take(pending.size - MAX_PENDING).forEach { pending.remove(it) }
        }
        val image = BitmapImageBuilder(uprightBitmap).build()
        landmarker.detectAsync(image, timestampMs)
    }

    override fun close() {
        pending.clear()
        landmarker.close()
    }

    companion object {
        const val MODEL_ASSET_PATH = "models/pose_landmarker_lite.task"
        private const val MAX_PENDING = 8

        /** True if the model file was bundled into assets by the build. */
        fun isModelBundled(context: Context): Boolean = runCatching {
            context.assets.openFd(MODEL_ASSET_PATH).use { it.length > 0 }
        }.getOrElse {
            runCatching { context.assets.open(MODEL_ASSET_PATH).use { true } }.getOrDefault(false)
        }

        /**
         * Creates the engine. Returns a failure (never a fake engine) if the model is missing
         * or MediaPipe cannot initialise on this device.
         */
        fun create(context: Context, onOutput: (PoseOutput) -> Unit): Result<MediaPipePoseEngine> = runCatching {
            check(isModelBundled(context)) { "Pose model is not bundled in this build" }
            val pending = ConcurrentHashMap<Long, PendingFrame>()
            val baseOptions = BaseOptions.builder()
                .setModelAssetPath(MODEL_ASSET_PATH)
                .setDelegate(Delegate.CPU)
                .build()
            val options = PoseLandmarker.PoseLandmarkerOptions.builder()
                .setBaseOptions(baseOptions)
                .setRunningMode(RunningMode.LIVE_STREAM)
                .setNumPoses(1)
                .setMinPoseDetectionConfidence(0.5f)
                .setMinPosePresenceConfidence(0.5f)
                .setMinTrackingConfidence(0.5f)
                .setResultListener { result: PoseLandmarkerResult, _ ->
                    onOutput(convert(result, pending))
                }
                .setErrorListener { error: RuntimeException ->
                    onOutput(PoseOutput.Error(error.message ?: "Pose model error"))
                }
                .build()
            MediaPipePoseEngine(PoseLandmarker.createFromOptions(context, options), pending)
        }

        private fun convert(result: PoseLandmarkerResult, pending: ConcurrentHashMap<Long, PendingFrame>): PoseOutput {
            val ts = result.timestampMs()
            val meta = pending.remove(ts)
                ?: return PoseOutput.Error("Result for unknown frame $ts")
            val inferenceMs = SystemClock.uptimeMillis() - meta.submittedAtMs
            val people = result.landmarks()
            if (people.isEmpty()) return PoseOutput.NoPerson(ts, inferenceMs)
            val person = people[0]
            if (person.size != BodyLandmark.COUNT) {
                return PoseOutput.Error("Unexpected landmark count ${person.size}")
            }
            val landmarks = person.map { lm ->
                Landmark(
                    x = lm.x(),
                    y = lm.y(),
                    z = lm.z(),
                    visibility = lm.visibility().orElse(0f),
                    presence = lm.presence().orElse(0f),
                )
            }
            return PoseOutput.Detected(
                frame = PoseFrame(
                    landmarks = landmarks,
                    timestampMs = ts,
                    imageWidth = meta.width,
                    imageHeight = meta.height,
                    previewMirrored = meta.previewMirrored,
                ),
                inferenceMs = inferenceMs,
            )
        }
    }
}
