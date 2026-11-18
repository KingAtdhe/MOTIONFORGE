package eu.motionforge.app.feature.settings

import android.Manifest
import android.content.pm.PackageManager
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import eu.motionforge.app.BuildConfig
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.data.UserPreferences

@Composable
fun ProfileScreen(
    preferences: UserPreferences,
    onOpenTechnicalChecks: () -> Unit,
    onResetData: () -> Unit,
) {
    val context = LocalContext.current
    fun granted() = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
    var cameraGranted by rememberSaveable { mutableStateOf(granted()) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { cameraGranted = granted() }
    var confirmReset by rememberSaveable { mutableStateOf(false) }

    ScreenColumn(title = "Profile") {
        Panel {
            Eyebrow("Training")
            Text("Focus: ${preferences.focus?.displayName ?: "not set"}", style = MaterialTheme.typography.bodyMedium)
            Text("Goal: ${preferences.goal?.displayName ?: "not set"}", style = MaterialTheme.typography.bodyMedium)
            Text("Account: guest (no account needed)", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Panel {
            Eyebrow("Camera & privacy")
            Text(
                "Camera images are processed on this phone to estimate body landmarks. Frames are kept in " +
                    "memory only — never saved, recorded or uploaded. The camera is only used while a camera " +
                    "screen is open.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Camera permission: " + if (cameraGranted) "granted" else "not granted",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Stored on this phone: your focus, goal and last viewed lesson. Nothing is sent to a server.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Panel {
            Eyebrow("Safety", color = MfColors.Caution)
            Text(
                "MOTIONFORGE is an educational practice companion for adults. It is not a medical device, does not " +
                    "diagnose or prevent injury, and does not replace a qualified trainer or instructor. Fighting " +
                    "fundamentals are non-contact only. Stop if you feel pain, dizziness or unusual discomfort.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Panel(onClick = onOpenTechnicalChecks) {
            Eyebrow("Developer")
            Text("Technical checks", style = MaterialTheme.typography.titleMedium)
            Text("Camera + pose tracking test and 3D animation test.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        OutlinedButton(
            onClick = { confirmReset = true },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MfColors.Halt),
        ) { Text("Reset app data") }
        Text(
            "Version ${BuildConfig.VERSION_NAME} · Intended for adults (18+).",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }

    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text("Reset app data?") },
            text = { Text("This deletes your focus, goal and lesson history from this phone and returns you to the welcome screens. It cannot be undone.") },
            confirmButton = {
                TextButton(onClick = {
                    confirmReset = false
                    onResetData()
                }) { Text("Reset", color = MfColors.Halt) }
            },
            dismissButton = { TextButton(onClick = { confirmReset = false }) { Text("Cancel") } },
        )
    }
}
