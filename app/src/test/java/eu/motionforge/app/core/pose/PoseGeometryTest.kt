package eu.motionforge.app.core.pose

import eu.motionforge.app.core.pose.PoseFixtures.landmark
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PoseGeometryTest {

    @Test
    fun rightAngleIsNinetyDegrees() {
        val angle = PoseGeometry.angleDegrees2d(
            a = landmark(0.5f, 0.0f), vertex = landmark(0.5f, 0.5f), b = landmark(1.0f, 0.5f),
            imageWidth = 100, imageHeight = 100,
        )
        assertEquals(90.0, angle!!, 1e-6)
    }

    @Test
    fun straightLineIsOneEightyDegrees() {
        val angle = PoseGeometry.angleDegrees2d(
            landmark(0.5f, 0.2f), landmark(0.5f, 0.5f), landmark(0.5f, 0.8f), 100, 100,
        )
        assertEquals(180.0, angle!!, 1e-6)
    }

    @Test
    fun aspectRatioIsRespected() {
        // In a 2:1 wide image, equal normalized offsets are not equal in pixels.
        // a = (+0.25, 0) -> (50px, 0); b = (0, +0.5) -> (0, 50px) => 90 degrees.
        val angle = PoseGeometry.angleDegrees2d(
            landmark(0.75f, 0.5f), landmark(0.5f, 0.5f), landmark(0.5f, 1.0f), imageWidth = 200, imageHeight = 100,
        )
        assertEquals(90.0, angle!!, 1e-6)
    }

    @Test
    fun degenerateSegmentReturnsNull() {
        val angle = PoseGeometry.angleDegrees2d(
            landmark(0.5f, 0.5f), landmark(0.5f, 0.5f), landmark(0.9f, 0.5f), 100, 100,
        )
        assertNull(angle)
    }

    @Test
    fun standingKneeIsNearlyStraight() {
        val f = PoseFixtures.standingFrame()
        val knee = PoseGeometry.angleDegrees2d(
            f[BodyLandmark.LEFT_HIP], f[BodyLandmark.LEFT_KNEE], f[BodyLandmark.LEFT_ANKLE], f.imageWidth, f.imageHeight,
        )
        assertEquals(180.0, knee!!, 1.0)
    }
}
