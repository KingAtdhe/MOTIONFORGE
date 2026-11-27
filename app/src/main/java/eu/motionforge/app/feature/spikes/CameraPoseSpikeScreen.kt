package eu.motionforge.app.feature.spikes

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import eu.motionforge.app.core.i18n.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import eu.motionforge.app.core.camera.CameraPreview
import eu.motionforge.app.core.camera.PoseFrameAnalyzer
import eu.motionforge.app.core.camera.PoseOverlay
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.design.ScreenHeader
import eu.motionforge.app.core.design.TrackingStatusChip
import eu.motionforge.app.core.pose.MediaPipePoseEngine
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseOutput
import eu.motionforge.app.core.pose.TrackingState
import eu.motionforge.app.core.pose.TrackingStateEvaluator

private enum class PermissionUi { RATIONALE, DENIED, GRANTED }

private fun Context.hasCameraPermission() =
    ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED

@Composable
fun CameraPoseSpikeScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    var permission by remember {
        mutableStateOf(if (context.hasCameraPermission()) PermissionUi.GRANTED else PermissionUi.RATIONALE)
    }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        permission = if (granted) PermissionUi.GRANTED else PermissionUi.DENIED
    }
    // Re-check when returning from system settings.
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        if (context.hasCameraPermission()) permission = PermissionUi.GRANTED
    }

    when (permission) {
        PermissionUi.RATIONALE -> ScreenColumn(title = "Camera check", onBack = onBack) {
            Panel {
                Eyebrow("Why the camera is needed")
                Text(
                    "MOTIONFORGE uses the camera to estimate the position of your joints while you practise. " +
                        "Images are processed on this phone, kept in memory only, and never saved or uploaded.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Button(onClick = { launcher.launch(Manifest.permission.CAMERA) }, modifier = Modifier.fillMaxWidth()) {
                Text("Allow camera")
            }
        }
        PermissionUi.DENIED -> ScreenColumn(title = "Camera check", onBack = onBack) {
            Panel {
                Eyebrow("Camera access denied", color = MfColors.Halt)
                Text(
                    "Live tracking needs camera access. 3D demonstrations and lessons still work without it.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Button(onClick = { launcher.launch(Manifest.permission.CAMERA) }, modifier = Modifier.fillMaxWidth()) {
                Text("Try again")
            }
            OutlinedButton(
                onClick = {
                    context.startActivity(
                        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", context.packageName, null))
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Open app settings") }
        }
        PermissionUi.GRANTED -> LiveCameraPose(onBack)
    }
}

/** UI state fed by pose results; updated on the main thread only. */
private class PoseSpikeState {
    val evaluator = TrackingStateEvaluator(TrackingStateEvaluator.FULL_BODY)
    var trackingState by mutableStateOf(TrackingState.CAMERA_INITIALIZING)
    var latestFrame by mutableStateOf<PoseFrame?>(null)
    var inferenceMs by mutableLongStateOf(0L)
    var processedFps by mutableFloatStateOf(0f)
    var lastError by mutableStateOf<String?>(null)
    var cameraReady by mutableStateOf(false)

    private var windowStartMs = 0L
    private var windowCount = 0

    fun onOutput(output: PoseOutput) {
        if (!cameraReady) return
        trackingState = evaluator.update(output)
        when (output) {
            is PoseOutput.Detected -> { latestFrame = output.frame; inferenceMs = output.inferenceMs }
            is PoseOutput.NoPerson -> { latestFrame = null; inferenceMs = output.inferenceMs }
            is PoseOutput.Error -> { latestFrame = null; lastError = output.message }
        }
        val now = SystemClock.uptimeMillis()
        if (windowStartMs == 0L) windowStartMs = now
        windowCount++
        val elapsed = now - windowStartMs
        if (elapsed >= 1000L) {
            processedFps = windowCount * 1000f / elapsed
            windowStartMs = now
            windowCount = 0
        }
    }

    fun onCameraRestart() {
        cameraReady = false
        latestFrame = null
        evaluator.reset()
        trackingState = TrackingState.CAMERA_INITIALIZING
    }
}

@Composable
private fun LiveCameraPose(onBack: () -> Unit) {
    val context = LocalContext.current
    val state = remember { PoseSpikeState() }
    var lensFacing by rememberSaveable { mutableIntStateOf(CameraSelector.LENS_FACING_FRONT) }
    var showOverlay by rememberSaveable { mutableStateOf(true) }
    var cameraError by remember { mutableStateOf<String?>(null) }
    var engineResult by remember { mutableStateOf<Result<MediaPipePoseEngine>?>(null) }

    DisposableEffect(Unit) {
        val main = Handler(Looper.getMainLooper())
        val result = MediaPipePoseEngine.create(context.applicationContext) { output ->
            main.post { state.onOutput(output) }
        }
        engineResult = result
        onDispose {
            main.removeCallbacksAndMessages(null)
            result.getOrNull()?.close()
        }
    }

    val engine = engineResult?.getOrNull()
    val mirrored = lensFacing == CameraSelector.LENS_FACING_FRONT
    val analyzer = remember(engine, mirrored) {
        engine?.let { e ->
            PoseFrameAnalyzer(e, previewMirrored = mirrored, onError = { msg -> state.lastError = msg })
        }
    }

    Column(Modifier.fillMaxSize()) {
        Box(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) { ScreenHeader("Camera & pose", onBack) }
        Box(
            Modifier
                .fillMaxWidth()
                .weight(1f)
                .background(MfColors.Night),
        ) {
            if (cameraError == null) {
                CameraPreview(
                    lensFacing = lensFacing,
                    analyzer = analyzer,
                    onCameraReady = { state.cameraReady = true },
                    onCameraError = { msg -> cameraError = msg },
                    modifier = Modifier.fillMaxSize(),
                )
                val frame = state.latestFrame
                if (showOverlay && frame != null) PoseOverlay(frame, Modifier.fillMaxSize())
            } else {
                Text(
                    "Camera unavailable: $cameraError",
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    color = MfColors.Halt,
                )
            }
            val chipState = when {
                cameraError != null -> TrackingState.CAMERA_ERROR
                engineResult?.isFailure == true -> null
                else -> state.trackingState
            }
            if (chipState != null) {
                TrackingStatusChip(chipState, Modifier.align(Alignment.TopCenter).padding(top = 12.dp))
            }
        }

        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            engineResult?.exceptionOrNull()?.let {
                Text(
                    "Pose model unavailable: ${it.message}. Camera preview still works; no tracking is shown.",
                    color = MfColors.Caution,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            if (engine != null) {
                Text(
                    "Inference ${state.inferenceMs} ms · ${"%.1f".format(state.processedFps)} results/s · " +
                        "landmarks ${if (state.latestFrame != null) 33 else 0}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            state.lastError?.let {
                Text("Last pipeline error: $it", style = MaterialTheme.typography.labelSmall, color = MfColors.Halt)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = {
                    state.onCameraRestart()
                    cameraError = null
                    lensFacing = if (lensFacing == CameraSelector.LENS_FACING_FRONT) {
                        CameraSelector.LENS_FACING_BACK
                    } else {
                        CameraSelector.LENS_FACING_FRONT
                    }
                }) { Text(if (mirrored) "Use rear camera" else "Use front camera") }
                OutlinedButton(onClick = { showOverlay = !showOverlay }) {
                    Text(if (showOverlay) "Hide skeleton" else "Show skeleton")
                }
            }
        }
    }
}
