package eu.motionforge.app.feature.catalog

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.ExerciseRepository

private sealed interface CatalogUiState {
    data object Loading : CatalogUiState
    data class Ready(val exercises: List<Exercise>) : CatalogUiState
    data class Error(val message: String) : CatalogUiState
}

/** Read-only catalogue preview for Phase 0. Lesson detail and filters come in Phase 1. */
@Composable
fun TrainScreen() {
    val context = LocalContext.current
    val repository = remember { ExerciseRepository(context.applicationContext) }
    val state by produceState<CatalogUiState>(CatalogUiState.Loading, repository) {
        value = repository.loadCatalog().fold(
            onSuccess = { CatalogUiState.Ready(it) },
            onFailure = { CatalogUiState.Error(it.message ?: "Could not read the lesson catalogue.") },
        )
    }

    ScreenColumn(title = "Train") {
        when (val s = state) {
            CatalogUiState.Loading -> Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp)
                Spacer(Modifier.width(12.dp))
                Text("Loading lessons…")
            }
            is CatalogUiState.Error -> Panel {
                Eyebrow("Error", color = MfColors.Halt)
                Text(s.message)
            }
            is CatalogUiState.Ready -> {
                if (s.exercises.isEmpty()) {
                    Panel { Text("No lessons are available in this build.") }
                } else {
                    TrainingCategory.entries.forEach { category ->
                        val items = s.exercises.filter { it.category == category }
                        if (items.isNotEmpty()) {
                            Eyebrow(category.displayName)
                            items.forEach { ExercisePreview(it) }
                        }
                    }
                    Text(
                        "Lesson details and practice sessions are added in Phase 1.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun ExercisePreview(exercise: Exercise) {
    Panel {
        Text(exercise.name, style = MaterialTheme.typography.titleMedium)
        Text(
            "${exercise.level.displayName} · ${exercise.durationSeconds}s · camera: ${exercise.recommendedView.displayName}",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            "Feedback: ${exercise.analysisMode.displayName}",
            style = MaterialTheme.typography.bodyMedium,
            color = if (exercise.analysisMode.allowsLiveCues) MfColors.Signal else MfColors.Muted,
        )
    }
}
