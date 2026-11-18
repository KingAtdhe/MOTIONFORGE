package eu.motionforge.app.feature.progress

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn

@Composable
fun ProgressScreen() {
    ScreenColumn(title = "Progress") {
        Panel {
            Text("No sessions yet", style = MaterialTheme.typography.titleMedium)
            Text(
                "Completed sessions will appear here once session tracking is built (Phase 5). " +
                    "History is stored on this phone only.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
