package eu.motionforge.app.feature.spikes

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn

/** Phase 0 technical spikes. Not part of the user-facing product flow. */
@Composable
fun SpikesScreen(onBack: () -> Unit, onOpenCameraPose: () -> Unit, onOpenGlb: () -> Unit) {
    ScreenColumn(title = "Technical checks", onBack = onBack) {
        Text(
            "These screens prove each pipeline works on your phone before product screens are built on top.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Panel(onClick = onOpenCameraPose) {
            Eyebrow("Spike 1 + 2")
            Text("Camera preview & pose tracking", style = MaterialTheme.typography.titleMedium)
            Text(
                "CameraX preview, on-device MediaPipe landmarks, tracking state and inference timing.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Panel(onClick = onOpenGlb) {
            Eyebrow("Spike 3")
            Text("3D model & animation", style = MaterialTheme.typography.titleMedium)
            Text(
                "Plays every trainer clip with orbit, view angles, pause, replay and slow motion.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
