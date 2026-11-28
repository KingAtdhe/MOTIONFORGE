package eu.motionforge.app.feature.settings

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.unit.dp
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.core.design.MotionForgeTheme
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.i18n.I18n
import eu.motionforge.app.core.i18n.I18nLoader
import eu.motionforge.app.core.i18n.LocalLanguage
import eu.motionforge.app.core.i18n.Text
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext

/**
 * The privacy note Health Connect shows for CORZA (from its permission screen, and on Android 14+ from the system's
 * permission usage screen): what the app writes, what it never does, and how to stop or delete.
 */
class HealthPermissionsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (applicationContext as MotionForgeApplication).container
        setContent {
            var lang by remember { mutableStateOf<String?>(null) }
            LaunchedEffect(Unit) {
                val wanted = I18n.resolve(runCatching { container.preferences.preferences.first().language }.getOrNull())
                withContext(Dispatchers.IO) { I18nLoader.apply(applicationContext, wanted) }
                lang = wanted
            }
            MotionForgeTheme {
                val applied = lang ?: return@MotionForgeTheme
                CompositionLocalProvider(LocalLanguage provides applied) {
                    ScreenColumn(title = "CORZA and Health Connect", onBack = { finish() }) {
                        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Text(
                                "When you turn it on in Profile, CORZA adds each session you save to Health Connect as a workout: its type, when it started and ended, and its title.",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Text(
                                "CORZA reads nothing from Health Connect. It does not write calories, heart rate or any other measurement, and it sends nothing to a server.",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Text(
                                "Turn it off in Profile at any time. Workouts already added stay in Health Connect until you delete them there.",
                                style = MaterialTheme.typography.bodyLarge,
                            )
                        }
                    }
                }
            }
        }
    }
}
