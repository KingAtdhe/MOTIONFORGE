package eu.motionforge.app.core.pose

/** Synthetic landmark fixtures for JVM tests. No real camera data is used in tests. */
object PoseFixtures {

    fun landmark(x: Float = 0.5f, y: Float = 0.5f, visibility: Float = 0.95f) =
        Landmark(x = x, y = y, z = 0f, visibility = visibility, presence = visibility)

    /** A plausible upright standing person, fully in frame, high confidence. */
    fun standingFrame(
        timestampMs: Long = 0L,
        overrides: Map<BodyLandmark, Landmark> = emptyMap(),
    ): PoseFrame {
        val base = MutableList(BodyLandmark.COUNT) { landmark() }
        fun set(lm: BodyLandmark, x: Float, y: Float) { base[lm.index] = landmark(x, y) }
        set(BodyLandmark.NOSE, 0.50f, 0.12f)
        set(BodyLandmark.LEFT_SHOULDER, 0.58f, 0.25f); set(BodyLandmark.RIGHT_SHOULDER, 0.42f, 0.25f)
        set(BodyLandmark.LEFT_ELBOW, 0.60f, 0.38f); set(BodyLandmark.RIGHT_ELBOW, 0.40f, 0.38f)
        set(BodyLandmark.LEFT_WRIST, 0.61f, 0.50f); set(BodyLandmark.RIGHT_WRIST, 0.39f, 0.50f)
        set(BodyLandmark.LEFT_HIP, 0.55f, 0.52f); set(BodyLandmark.RIGHT_HIP, 0.45f, 0.52f)
        set(BodyLandmark.LEFT_KNEE, 0.55f, 0.70f); set(BodyLandmark.RIGHT_KNEE, 0.45f, 0.70f)
        set(BodyLandmark.LEFT_ANKLE, 0.55f, 0.88f); set(BodyLandmark.RIGHT_ANKLE, 0.45f, 0.88f)
        overrides.forEach { (lm, value) -> base[lm.index] = value }
        return PoseFrame(base, timestampMs, imageWidth = 480, imageHeight = 640, previewMirrored = true)
    }

    fun detected(frame: PoseFrame) = PoseOutput.Detected(frame, inferenceMs = 30)
}
