package eu.motionforge.app.core.pose

/**
 * MOTIONFORGE's own pose types. Raw MediaPipe types never leave the pose package
 * (see [MediaPipePoseEngine]); everything downstream uses these.
 */

/** The 33 landmarks of the MediaPipe pose topology, in model output order. */
enum class BodyLandmark(val index: Int) {
    NOSE(0),
    LEFT_EYE_INNER(1), LEFT_EYE(2), LEFT_EYE_OUTER(3),
    RIGHT_EYE_INNER(4), RIGHT_EYE(5), RIGHT_EYE_OUTER(6),
    LEFT_EAR(7), RIGHT_EAR(8),
    MOUTH_LEFT(9), MOUTH_RIGHT(10),
    LEFT_SHOULDER(11), RIGHT_SHOULDER(12),
    LEFT_ELBOW(13), RIGHT_ELBOW(14),
    LEFT_WRIST(15), RIGHT_WRIST(16),
    LEFT_PINKY(17), RIGHT_PINKY(18),
    LEFT_INDEX(19), RIGHT_INDEX(20),
    LEFT_THUMB(21), RIGHT_THUMB(22),
    LEFT_HIP(23), RIGHT_HIP(24),
    LEFT_KNEE(25), RIGHT_KNEE(26),
    LEFT_ANKLE(27), RIGHT_ANKLE(28),
    LEFT_HEEL(29), RIGHT_HEEL(30),
    LEFT_FOOT_INDEX(31), RIGHT_FOOT_INDEX(32);

    companion object {
        const val COUNT = 33
        private val byIndex = entries.associateBy { it.index }
        fun fromIndex(index: Int): BodyLandmark? = byIndex[index]
    }
}

/**
 * One landmark in normalized image coordinates of the *unmirrored* camera image,
 * after rotation to upright: x and y in [0,1] when inside the image, z relative depth.
 * [visibility] and [presence] are model confidences in [0,1].
 */
data class Landmark(
    val x: Float,
    val y: Float,
    val z: Float,
    val visibility: Float,
    val presence: Float,
)

/** A single inference result for one person. */
data class PoseFrame(
    /** Indexed by [BodyLandmark.index]; always [BodyLandmark.COUNT] long. */
    val landmarks: List<Landmark>,
    val timestampMs: Long,
    /** Upright (rotation applied) image size that the landmarks are normalized against. */
    val imageWidth: Int,
    val imageHeight: Int,
    /** True when the on-screen preview is mirrored (front camera). Landmarks themselves are not mirrored. */
    val previewMirrored: Boolean,
) {
    init {
        require(landmarks.size == BodyLandmark.COUNT) { "Expected ${BodyLandmark.COUNT} landmarks, got ${landmarks.size}" }
    }

    operator fun get(landmark: BodyLandmark): Landmark = landmarks[landmark.index]
}

/** What the pose engine reports per processed frame. */
sealed interface PoseOutput {
    /** The model ran and found no person. */
    data class NoPerson(val timestampMs: Long, val inferenceMs: Long) : PoseOutput

    data class Detected(val frame: PoseFrame, val inferenceMs: Long) : PoseOutput

    data class Error(val message: String) : PoseOutput
}

/** Skeleton edges used for the debug overlay. */
val POSE_CONNECTIONS: List<Pair<BodyLandmark, BodyLandmark>> = listOf(
    BodyLandmark.LEFT_SHOULDER to BodyLandmark.RIGHT_SHOULDER,
    BodyLandmark.LEFT_SHOULDER to BodyLandmark.LEFT_ELBOW,
    BodyLandmark.LEFT_ELBOW to BodyLandmark.LEFT_WRIST,
    BodyLandmark.RIGHT_SHOULDER to BodyLandmark.RIGHT_ELBOW,
    BodyLandmark.RIGHT_ELBOW to BodyLandmark.RIGHT_WRIST,
    BodyLandmark.LEFT_SHOULDER to BodyLandmark.LEFT_HIP,
    BodyLandmark.RIGHT_SHOULDER to BodyLandmark.RIGHT_HIP,
    BodyLandmark.LEFT_HIP to BodyLandmark.RIGHT_HIP,
    BodyLandmark.LEFT_HIP to BodyLandmark.LEFT_KNEE,
    BodyLandmark.LEFT_KNEE to BodyLandmark.LEFT_ANKLE,
    BodyLandmark.RIGHT_HIP to BodyLandmark.RIGHT_KNEE,
    BodyLandmark.RIGHT_KNEE to BodyLandmark.RIGHT_ANKLE,
    BodyLandmark.LEFT_ANKLE to BodyLandmark.LEFT_HEEL,
    BodyLandmark.LEFT_HEEL to BodyLandmark.LEFT_FOOT_INDEX,
    BodyLandmark.RIGHT_ANKLE to BodyLandmark.RIGHT_HEEL,
    BodyLandmark.RIGHT_HEEL to BodyLandmark.RIGHT_FOOT_INDEX,
)
