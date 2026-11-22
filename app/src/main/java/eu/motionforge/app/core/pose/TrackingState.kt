package eu.motionforge.app.core.pose

/**
 * Camera/tracking states from docs/MOVEMENT_ANALYSIS_AND_SAFETY.md §2.
 * Movement feedback may only be shown in [TRACKING].
 */
enum class TrackingState(val userMessage: String) {
    CAMERA_PERMISSION_REQUIRED("Camera access is needed for live tracking."),
    CAMERA_PERMISSION_DENIED("Camera access was denied. Demo mode still works."),
    CAMERA_INITIALIZING("Starting camera…"),
    MOVE_INTO_VIEW("Move into view"),
    ADJUST_CAMERA("Adjust camera — part of your body is out of frame"),
    CALIBRATING("Hold position"),
    TRACKING("Tracking"),
    LOW_CONFIDENCE("Unable to assess — tracking confidence is low"),
    OCCLUDED("Unable to assess — some joints are hidden"),
    UNSUPPORTED_VIEW("I can't assess this movement from the current angle"),
    PAUSED("Paused"),
    CAMERA_ERROR("Camera unavailable"),
    ;

    val allowsFeedback: Boolean get() = this == TRACKING
}

/**
 * Turns a stream of pose results into a [TrackingState]. Pure Kotlin, no Android types,
 * so it is covered by JVM unit tests.
 *
 * Rules (initial hypotheses, to be calibrated on real devices — see validation plan):
 * - No person → MOVE_INTO_VIEW.
 * - A required landmark outside the image (with a small edge margin) → ADJUST_CAMERA.
 * - Mean visibility of required landmarks below [minVisibility] → LOW_CONFIDENCE.
 * - Mean is fine but at least one required landmark is below [minVisibility] → OCCLUDED.
 * - Otherwise the frame is "good". TRACKING is only reported after [stableFramesRequired]
 *   consecutive good frames; before that the state is CALIBRATING. Any bad frame resets
 *   the streak, so a single good frame can never unlock feedback.
 */
class TrackingStateEvaluator(
    private val requiredLandmarks: Set<BodyLandmark>,
    private val minVisibility: Float = 0.6f,
    private val edgeMargin: Float = 0.02f,
    private val stableFramesRequired: Int = 5,
    /**
     * Side-on support: when true, a left/right pair of required landmarks counts as seen when the side nearer the
     * camera is clearly visible (the far knee or elbow is hidden behind the body when filmed from the side). The
     * near side is the one whose required landmarks are, at worst, most visible; it must pass every test on its own.
     */
    private val eitherSide: Boolean = false,
) {
    init {
        require(requiredLandmarks.isNotEmpty()) { "At least one required landmark" }
        require(minVisibility in 0f..1f)
        require(stableFramesRequired >= 2) { "TRACKING must never come from a single frame" }
    }

    private var goodStreak = 0

    val consecutiveGoodFrames: Int get() = goodStreak

    fun reset() {
        goodStreak = 0
    }

    fun update(output: PoseOutput): TrackingState = when (output) {
        is PoseOutput.Error -> { goodStreak = 0; TrackingState.CAMERA_ERROR }
        is PoseOutput.NoPerson -> { goodStreak = 0; TrackingState.MOVE_INTO_VIEW }
        is PoseOutput.Detected -> evaluateFrame(output.frame)
    }

    private fun evaluateFrame(frame: PoseFrame): TrackingState {
        val required = (if (eitherSide) nearSide(frame) else requiredLandmarks).map { frame[it] }

        val outOfFrame = required.any { lm ->
            lm.x < edgeMargin || lm.x > 1f - edgeMargin || lm.y < edgeMargin || lm.y > 1f - edgeMargin
        }
        if (outOfFrame) {
            goodStreak = 0
            return TrackingState.ADJUST_CAMERA
        }

        val meanVisibility = required.map { it.visibility }.average()
        if (meanVisibility < minVisibility) {
            goodStreak = 0
            return TrackingState.LOW_CONFIDENCE
        }
        if (required.any { it.visibility < minVisibility }) {
            goodStreak = 0
            return TrackingState.OCCLUDED
        }

        goodStreak++
        return if (goodStreak >= stableFramesRequired) TrackingState.TRACKING else TrackingState.CALIBRATING
    }

    /** The required landmarks with every left/right pair narrowed to one side: the side seen best overall. */
    private fun nearSide(frame: PoseFrame): Set<BodyLandmark> {
        val left = requiredLandmarks.filter { it.name.startsWith("LEFT_") }
        val right = requiredLandmarks.filter { it.name.startsWith("RIGHT_") }
        val centre = requiredLandmarks - left.toSet() - right.toSet()
        if (left.isEmpty() || right.isEmpty()) return requiredLandmarks
        val worstLeft = left.minOf { frame[it].visibility }
        val worstRight = right.minOf { frame[it].visibility }
        val near = if (worstLeft >= worstRight) left else right
        // the torso (both shoulders, both hips) stays required on both sides: it is never hidden side-on
        val torso = requiredLandmarks.filter { it.name.endsWith("_SHOULDER") || it.name.endsWith("_HIP") }
        return (centre + near + torso).toSet()
    }

    companion object {
        /** Landmarks needed to say the whole body is in view (squat, footwork, stance). */
        val FULL_BODY: Set<BodyLandmark> = setOf(
            BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER,
            BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP,
            BodyLandmark.LEFT_KNEE, BodyLandmark.RIGHT_KNEE,
            BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE,
        )
    }
}
