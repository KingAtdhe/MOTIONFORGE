package eu.motionforge.app.feature.settings

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.core.i18n.Text
import eu.motionforge.app.core.i18n.tr
import eu.motionforge.app.data.HealthConnectSync
import eu.motionforge.app.data.UserPreferences
import kotlinx.coroutines.launch

/**
 * Profile → Health Connect. Says what is shared before anything is asked; the system's permission screen comes only
 * when the switch is turned on. Off by default; turning it off stops new entries at once.
 */
@Composable
fun HealthConnectSetting(preferences: UserPreferences) {
    val context = LocalContext.current
    val container = remember { (context.applicationContext as MotionForgeApplication).container }
    val sync = container.healthConnect
    val scope = rememberCoroutineScope()
    var availability by remember { mutableStateOf(sync.availability()) }
    var granted by remember { mutableStateOf<Boolean?>(null) }
    var refused by rememberSaveable { mutableStateOf(false) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        availability = sync.availability()
        scope.launch { granted = sync.hasPermission() }
    }
    val ask = rememberLauncherForActivityResult(PermissionController.createRequestPermissionResultContract()) { got ->
        val ok = got.containsAll(HealthConnectSync.PERMISSIONS)
        granted = ok
        refused = !ok
        scope.launch { container.preferences.setHealthConnect(ok) }
    }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            "Adds each session you save to Health Connect as a workout: its type, when it started and ended, and its title. CORZA writes nothing else and reads nothing from Health Connect.",
            style = MaterialTheme.typography.bodyMedium,
        )
        when (availability) {
            HealthConnectSync.Availability.UNAVAILABLE -> Text(
                "Health Connect isn't available on this phone.",
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            HealthConnectSync.Availability.NEEDS_INSTALL_OR_UPDATE -> {
                Text(
                    "Health Connect needs to be installed or updated first.",
                    style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                TextButton(onClick = { openStore(context) }) { Text("Get Health Connect") }
            }
            HealthConnectSync.Availability.AVAILABLE -> {
                val on = preferences.healthConnect && granted != false
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Add sessions to Health Connect", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                    Switch(
                        checked = on,
                        onCheckedChange = { want ->
                            if (want) {
                                refused = false
                                ask.launch(HealthConnectSync.PERMISSIONS)
                            } else scope.launch { container.preferences.setHealthConnect(false) }
                        },
                        modifier = Modifier.semantics { contentDescription = tr("Add sessions to Health Connect") },
                    )
                }
                when {
                    refused -> Text(
                        "Health Connect access wasn't given, so nothing is added.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    preferences.healthConnect && granted == false -> Text(
                        "Health Connect access was removed, so nothing is added. Turn this on again to allow it.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    on -> Text(
                        "New sessions are added when you save them. Workouts already added stay in Health Connect until you delete them there.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

private fun openStore(context: android.content.Context) {
    val market = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=${HealthConnectSync.PROVIDER}&url=healthconnect%3A%2F%2Fonboarding"))
        .setPackage("com.android.vending").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    try {
        context.startActivity(market)
    } catch (e: ActivityNotFoundException) {
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=${HealthConnectSync.PROVIDER}"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    }
}
