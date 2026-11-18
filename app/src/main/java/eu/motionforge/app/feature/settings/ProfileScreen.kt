package eu.motionforge.app.feature.settings

import android.Manifest
import android.content.pm.PackageManager
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import eu.motionforge.app.BuildConfig
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn

@Composable
fun ProfileScreen() {
    val context = LocalContext.current
    val cameraGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
        PackageManager.PERMISSION_GRANTED

    ScreenColumn(title = "Profile") {
        Panel {
            Eyebrow("Camera & privacy")
            Text(
                "Camera images are processed on this phone to estimate body landmarks. Frames are kept in " +
                    "memory only — they are never saved, recorded or uploaded.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Camera permission: " + if (cameraGranted) "granted" else "not granted",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Panel {
            Eyebrow("Account")
            Text(
                "Guest mode. No account is needed. Optional sync is planned for a later phase.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Panel {
            Eyebrow("About")
            Text("Version ${BuildConfig.VERSION_NAME}", style = MaterialTheme.typography.bodyMedium)
            Text(
                "Intended for adults (18+). Not a medical device.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
