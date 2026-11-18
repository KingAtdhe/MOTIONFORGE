package eu.motionforge.app.feature.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.FactChip
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.catalog.CatalogUiState
import eu.motionforge.app.feature.catalog.LessonSuggestions

@Composable
fun HomeScreen(
    preferences: UserPreferences,
    catalog: CatalogUiState,
    onOpenLesson: (String) -> Unit,
    onOpenCategory: (TrainingCategory) -> Unit,
    onRetry: () -> Unit,
) {
    ScreenColumn(title = "Welcome") {
        val focusText = preferences.focus?.displayName ?: "All lessons"
        val goalText = preferences.goal?.displayName
        Text(
            if (goalText != null) "Focus: $focusText · Goal: $goalText" else "Focus: $focusText",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        when (catalog) {
            CatalogUiState.Loading -> Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp)
                Spacer(Modifier.width(12.dp))
                Text("Loading lessons…")
            }
            is CatalogUiState.Error -> Panel {
                Eyebrow("Lessons unavailable", color = MfColors.Halt)
                Text(catalog.message, style = MaterialTheme.typography.bodyMedium)
                OutlinedButton(onClick = onRetry) { Text("Try again") }
            }
            is CatalogUiState.Ready -> {
                val exercises = catalog.exercises
                val lastViewed = exercises.firstOrNull { it.id == preferences.lastViewedExerciseId }
                val suggestion = LessonSuggestions.suggest(exercises, preferences.focus, preferences.goal, preferences.lastViewedExerciseId)

                if (lastViewed != null) {
                    LessonCard("Continue where you left off", lastViewed, onOpenLesson)
                }
                if (suggestion != null) {
                    LessonCard("Suggested next", suggestion, onOpenLesson)
                } else if (lastViewed == null) {
                    Panel { Text("No lessons are available in this build.") }
                }

                Eyebrow("Categories")
                TrainingCategory.entries.forEach { category ->
                    val count = exercises.count { it.category == category }
                    Panel(onClick = { onOpenCategory(category) }) {
                        Text(category.displayName, style = MaterialTheme.typography.titleMedium)
                        Text(
                            "$count beginner lessons",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        Panel {
            Eyebrow("Safety reminder", color = MfColors.Caution)
            Text(
                "Train in clear space, at your own pace. Stop if you feel pain, dizziness or unusual discomfort. " +
                    "MOTIONFORGE does not replace a qualified trainer or instructor.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun LessonCard(label: String, exercise: Exercise, onOpenLesson: (String) -> Unit) {
    Panel(onClick = { onOpenLesson(exercise.id) }) {
        Eyebrow(label)
        Text(exercise.name, style = MaterialTheme.typography.titleLarge)
        Text(exercise.purpose, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FactChip(exercise.category.displayName)
            FactChip("${exercise.durationSeconds} s")
        }
    }
}
