package eu.motionforge.app.core.camera

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.POSE_CONNECTIONS
import eu.motionforge.app.core.pose.PoseFrame

/**
 * Draws landmarks over a FIT_CENTER camera preview. Landmarks below [minVisibility] are
 * drawn faint so the user can see what the model is unsure about.
 */
@Composable
fun PoseOverlay(
    frame: PoseFrame,
    modifier: Modifier = Modifier,
    minVisibility: Float = 0.6f,
    confidentColor: Color = Color.White,
    uncertainColor: Color = Color(0x66FFFFFF),
) {
    Canvas(modifier = modifier) {
        val imageAspect = frame.imageWidth.toFloat() / frame.imageHeight
        val viewAspect = size.width / size.height
        val drawW: Float
        val drawH: Float
        if (imageAspect > viewAspect) {
            drawW = size.width; drawH = size.width / imageAspect
        } else {
            drawH = size.height; drawW = size.height * imageAspect
        }
        val left = (size.width - drawW) / 2f
        val top = (size.height - drawH) / 2f

        fun Landmark.toOffset(): Offset {
            val nx = if (frame.previewMirrored) 1f - x else x
            return Offset(left + nx * drawW, top + y * drawH)
        }

        POSE_CONNECTIONS.forEach { (a, b) ->
            val la = frame[a]
            val lb = frame[b]
            val confident = la.visibility >= minVisibility && lb.visibility >= minVisibility
            drawLine(
                color = if (confident) confidentColor else uncertainColor,
                start = la.toOffset(),
                end = lb.toOffset(),
                strokeWidth = 6f,
                cap = StrokeCap.Round,
            )
        }
        // joints as small timing-yellow marks: the "geometric chronophotograph" look of the motion studies
        frame.landmarks.forEachIndexed { i, lm ->
            if (i in 1..10) return@forEachIndexed   // face points: keep the trace about the body, not the face
            drawCircle(
                color = if (lm.visibility >= minVisibility) Color(0xFFFFD60A) else uncertainColor,
                radius = 6f,
                center = lm.toOffset(),
            )
        }
    }
}
