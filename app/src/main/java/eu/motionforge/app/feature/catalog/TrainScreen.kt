package eu.motionforge.app.feature.catalog

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.ChoiceButton
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.LessonCard
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory

@Composable
fun TrainScreen(
    catalog: CatalogUiState,
    filter: CatalogFilter,
    onCategory: (TrainingCategory?) -> Unit,
    onDuration: (DurationFilter) -> Unit,
    onClearFilters: () -> Unit,
    onOpenLesson: (String) -> Unit,
    onRetry: () -> Unit,
) {
    ScreenColumn(title = "Train") {
        Eyebrow("Category")
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ChoiceButton("All", filter.category == null, { onCategory(null) })
            TrainingCategory.entries.forEach { c ->
                ChoiceButton(c.displayName, filter.category == c, { onCategory(c) })
            }
        }
        Eyebrow("Length")
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            DurationFilter.entries.forEach { d -> ChoiceButton(d.label, filter.duration == d, { onDuration(d) }) }
        }

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
                val visible = filter.apply(catalog.exercises)
                when {
                    catalog.exercises.isEmpty() -> Panel { Text("No lessons are available in this build.") }
                    visible.isEmpty() -> Panel {
                        Text("No lessons match these filters.", style = MaterialTheme.typography.titleMedium)
                        OutlinedButton(onClick = onClearFilters) { Text("Clear filters") }
                    }
                    else -> {
                        Text(
                            "${visible.size} lesson${if (visible.size == 1) "" else "s"} · all beginner level",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        visible.forEach { LessonRow(it, onOpenLesson) }
                    }
                }
            }
        }
    }
}

@Composable
private fun LessonRow(exercise: Exercise, onOpenLesson: (String) -> Unit) {
    LessonCard(
        title = exercise.name,
        subtitle = exercise.purpose,
        facts = listOf(exercise.category.displayName, "${exercise.durationSeconds} s"),
        accent = exercise.category.accent,
        onClick = { onOpenLesson(exercise.id) },
    )
}
