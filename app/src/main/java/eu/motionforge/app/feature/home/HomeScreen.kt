package eu.motionforge.app.feature.home

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
import eu.motionforge.app.core.design.HeroCard
import eu.motionforge.app.core.design.LessonCard
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.feature.session.SessionPlanner
import eu.motionforge.app.feature.session.SessionStep
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
    onStartQuickSession: () -> Unit,
    sessionsThisWeek: Int?,
    onRetry: () -> Unit,
) {
    ScreenColumn(title = "Ready to move?") {
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

                val accent = (preferences.focus ?: TrainingCategory.FITNESS).accent
                val quick = SessionPlanner.quick(exercises, preferences.focus)
                if (quick != null) {
                    HeroCard(
                        eyebrow = "Today · about ${(quick.totalSeconds + 30) / 60} min",
                        title = quick.title,
                        body = quick.steps.filterIsInstance<SessionStep.Work>().joinToString(" → ") { it.name },
                        action = "Start session",
                        accent = accent,
                        onClick = onStartQuickSession,
                    )
                } else {
                    Panel { Text("No lessons are available in this build.") }
                }
                if (sessionsThisWeek != null) {
                    Text(
                        if (sessionsThisWeek == 0) "No sessions saved this week yet." else "$sessionsThisWeek session${if (sessionsThisWeek == 1) "" else "s"} saved this week.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (lastViewed != null) {
                    HomeLesson("Continue where you left off", lastViewed, onOpenLesson)
                }
                if (suggestion != null) {
                    HomeLesson("Suggested lesson", suggestion, onOpenLesson)
                }

                Eyebrow("Categories")
                TrainingCategory.entries.forEach { category ->
                    val count = exercises.count { it.category == category }
                    LessonCard(
                        title = category.displayName,
                        subtitle = "$count beginner lessons",
                        facts = emptyList(),
                        accent = category.accent,
                        onClick = { onOpenCategory(category) },
                    )
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
private fun HomeLesson(label: String, exercise: Exercise, onOpenLesson: (String) -> Unit) {
    LessonCard(
        title = exercise.name,
        subtitle = exercise.purpose,
        facts = listOf(exercise.category.displayName, "${exercise.durationSeconds} s"),
        accent = exercise.category.accent,
        onClick = { onOpenLesson(exercise.id) },
        eyebrow = label,
    )
}
