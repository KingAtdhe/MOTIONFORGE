package eu.motionforge.app.feature.home

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn

@Composable
fun HomeScreen(onOpenSpikes: () -> Unit) {
    ScreenColumn(title = "MOTIONFORGE") {
        Text(
            "See the movement. Practise it. Understand your progress.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Panel {
            Eyebrow("Safety", color = MfColors.Caution)
            Text(
                "MOTIONFORGE is an educational practice companion for adults. It is not a medical device and " +
                    "does not replace a qualified trainer or martial arts instructor. Stop if you feel pain, " +
                    "dizziness or unusual discomfort.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        Panel {
            Eyebrow("Build status")
            Text("Phase 0 — technical foundation", style = MaterialTheme.typography.titleMedium)
            Text(
                "Training sessions, onboarding and progress arrive in later phases. This build exists to prove " +
                    "the camera, pose tracking and 3D pipelines on real phones.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Panel(onClick = onOpenSpikes) {
            Eyebrow("Developer")
            Text("Technical checks", style = MaterialTheme.typography.titleMedium)
            Text(
                "Camera + pose tracking test and 3D animation test.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
