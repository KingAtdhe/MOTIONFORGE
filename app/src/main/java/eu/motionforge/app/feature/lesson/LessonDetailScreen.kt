package eu.motionforge.app.feature.lesson

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.FactChip
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.ReviewStatus
import eu.motionforge.app.feature.catalog.CatalogUiState

@Composable
fun LessonDetailScreen(
    lessonId: String,
    catalog: CatalogUiState,
    onBack: () -> Unit,
    onViewed: (String) -> Unit,
    onRetry: () -> Unit,
) {
    when (catalog) {
        CatalogUiState.Loading -> ScreenColumn(title = "Lesson", onBack = onBack) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp)
                Spacer(Modifier.width(12.dp))
                Text("Loading lesson…")
            }
        }
        is CatalogUiState.Error -> ScreenColumn(title = "Lesson", onBack = onBack) {
            Panel {
                Eyebrow("Lesson unavailable", color = MfColors.Halt)
                Text(catalog.message, style = MaterialTheme.typography.bodyMedium)
                OutlinedButton(onClick = onRetry) { Text("Try again") }
            }
        }
        is CatalogUiState.Ready -> {
            val exercise = catalog.exercises.firstOrNull { it.id == lessonId }
            if (exercise == null) {
                ScreenColumn(title = "Lesson", onBack = onBack) {
                    Panel { Text("This lesson isn't available in this version of the app.") }
                }
            } else {
                LaunchedEffect(exercise.id) { onViewed(exercise.id) }
                LessonDetail(exercise, onBack)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun LessonDetail(exercise: Exercise, onBack: () -> Unit) {
    ScreenColumn(title = exercise.name, onBack = onBack) {
        Text(exercise.purpose, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            FactChip(exercise.category.displayName)
            FactChip(exercise.level.displayName)
            FactChip("${exercise.durationSeconds} s")
            FactChip("Camera: ${exercise.recommendedView.displayName}")
        }

        if (exercise.reviewStatus == ReviewStatus.DRAFT_PENDING_COACH_REVIEW) {
            Text(
                "Draft instructions — pending review by a qualified coach.",
                style = MaterialTheme.typography.labelSmall,
                color = MfColors.Caution,
            )
        }

        Panel {
            Eyebrow("Safety", color = MfColors.Caution)
            Text(exercise.safety, style = MaterialTheme.typography.bodyMedium)
        }

        Panel {
            Eyebrow("Space & equipment")
            Text(exercise.space, style = MaterialTheme.typography.bodyMedium)
            Text(
                if (exercise.equipment.isEmpty()) "No equipment needed." else exercise.equipment.joinToString(" · "),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Panel {
            Eyebrow("3D demonstration")
            Text(
                if (exercise.demoAnimation != null) {
                    "The 3D trainer demonstration for this lesson arrives with the trainer model. " +
                        "Until then, follow the written steps below."
                } else {
                    "This lesson is taught with written steps only."
                },
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        SectionTitle("How to do it")
        exercise.instructions.forEachIndexed { i, step ->
            Row {
                Text("${i + 1}.", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.width(12.dp))
                Text(step, style = MaterialTheme.typography.bodyLarge)
            }
        }

        if (exercise.commonCues.isNotEmpty()) {
            SectionTitle("Keep in mind")
            exercise.commonCues.forEach { Text("•  $it", style = MaterialTheme.typography.bodyMedium) }
        }

        if (exercise.commonMistakes.isNotEmpty()) {
            SectionTitle("Common mistakes")
            exercise.commonMistakes.forEach { m ->
                Panel {
                    Text(m.mistake, style = MaterialTheme.typography.titleMedium)
                    Text("Try: ${m.adjustment}", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        Panel {
            Eyebrow("Camera feedback")
            Text(exercise.analysisMode.displayName, style = MaterialTheme.typography.titleMedium)
            Text(exercise.limitations, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "Camera-guided practice is not available in this build yet.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
}
