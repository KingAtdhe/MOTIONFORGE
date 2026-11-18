package eu.motionforge.app.core.pose

import kotlin.math.acos
import kotlin.math.sqrt

object PoseGeometry {

    /**
     * Angle at [vertex] formed by [a]-[vertex]-[b], in degrees [0, 180], using 2D image
     * coordinates scaled to the real image aspect ratio (normalized x and y are not on the
     * same scale unless the image is square).
     *
     * Returns null when either arm of the angle is degenerate (points coincide), because
     * an angle there would be noise, not a measurement.
     */
    fun angleDegrees2d(
        a: Landmark,
        vertex: Landmark,
        b: Landmark,
        imageWidth: Int,
        imageHeight: Int,
    ): Double? {
        require(imageWidth > 0 && imageHeight > 0) { "Image size must be positive" }
        val ax = (a.x - vertex.x).toDouble() * imageWidth
        val ay = (a.y - vertex.y).toDouble() * imageHeight
        val bx = (b.x - vertex.x).toDouble() * imageWidth
        val by = (b.y - vertex.y).toDouble() * imageHeight
        val lenA = sqrt(ax * ax + ay * ay)
        val lenB = sqrt(bx * bx + by * by)
        if (lenA < MIN_SEGMENT_PX || lenB < MIN_SEGMENT_PX) return null
        val cos = ((ax * bx + ay * by) / (lenA * lenB)).coerceIn(-1.0, 1.0)
        return Math.toDegrees(acos(cos))
    }

    /** Segments shorter than this many pixels are treated as degenerate. */
    const val MIN_SEGMENT_PX = 1.0
}
