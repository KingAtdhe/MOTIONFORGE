package eu.motionforge.app.core.camera

import android.os.Handler
import android.os.Looper
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import eu.motionforge.app.core.i18n.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.camera.core.CameraSelector
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.pose.MediaPipePoseEngine
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseOutput

/**
 * Live camera with on-device pose tracking and an optional skeleton overlay.
 * Pose results are delivered on the main thread through [onOutput]. If the camera or the pose
 * model is unavailable, a plain message is shown and no results are produced (never faked).
 * Requires the CAMERA permission to be granted already.
 */
@Composable
fun PoseCameraPane(
    lensFacing: Int,
    showOverlay: Boolean,
    onOutput: (PoseOutput) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val currentOnOutput by rememberUpdatedState(onOutput)
    var latestFrame by remember { mutableStateOf<PoseFrame?>(null) }
    var cameraReady by remember(lensFacing) { mutableStateOf(false) }
    var cameraError by remember(lensFacing) { mutableStateOf<String?>(null) }
    var engineResult by remember { mutableStateOf<Result<MediaPipePoseEngine>?>(null) }

    DisposableEffect(Unit) {
        val main = Handler(Looper.getMainLooper())
        var active = true
        val result = MediaPipePoseEngine.create(context.applicationContext) { output ->
            main.post {
                if (!active) return@post
                latestFrame = (output as? PoseOutput.Detected)?.frame
                currentOnOutput(output)
            }
        }
        engineResult = result
        onDispose {
            active = false
            main.removeCallbacksAndMessages(null)
            result.getOrNull()?.close()
        }
    }

    val engine = engineResult?.getOrNull()
    val mirrored = lensFacing == CameraSelector.LENS_FACING_FRONT
    val analyzer = remember(engine, mirrored) {
        engine?.let { PoseFrameAnalyzer(it, previewMirrored = mirrored, onError = { }) }
    }

    Box(modifier.background(MfColors.Night)) {
        val error = cameraError
        if (error == null) {
            CameraPreview(
                lensFacing = lensFacing,
                analyzer = analyzer,
                onCameraReady = { cameraReady = true },
                onCameraError = { cameraError = it },
                modifier = Modifier.fillMaxSize(),
            )
            val frame = latestFrame
            if (showOverlay && cameraReady && frame != null) PoseOverlay(frame, Modifier.fillMaxSize())
        } else {
            Text("Camera unavailable: $error", Modifier.align(Alignment.Center).padding(24.dp), color = MfColors.Halt)
        }
        if (engineResult?.isFailure == true) {
            Text(
                "Pose tracking is unavailable in this build, so nothing is assessed.",
                Modifier.align(Alignment.BottomCenter).padding(12.dp),
                style = MaterialTheme.typography.labelMedium,
                color = MfColors.Caution,
            )
        }
    }
}
