package eu.motionforge.app.feature.catalog

import eu.motionforge.app.core.design.LessonRow
import eu.motionforge.app.core.design.ThinRule
import eu.motionforge.app.core.design.SectionHeader
import eu.motionforge.app.core.design.formatClock
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.height
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
import eu.motionforge.app.core.design.SegmentedPill
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.LessonTile
import eu.motionforge.app.core.design.formatLength
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory

@Composable
fun TrainScreen(
    catalog: CatalogUiState,
    coach: Coach,
    filter: CatalogFilter,
    onCategory: (TrainingCategory?) -> Unit,
    onDuration: (DurationFilter) -> Unit,
    onEquipment: (EquipmentFilter) -> Unit,
    onClearFilters: () -> Unit,
    onOpenLesson: (String) -> Unit,
    onRetry: () -> Unit,
) {
    ScreenColumn(title = "Train") {
        val categories = listOf<TrainingCategory?>(null) + TrainingCategory.entries
        SegmentedPill(
            options = categories.map { it?.let { c -> if (c == TrainingCategory.FIGHTING_FUNDAMENTALS) "Fighting" else c.displayName } ?: "All" },
            selectedIndex = categories.indexOf(filter.category),
            onSelect = { onCategory(categories[it]) },
            modifier = Modifier.horizontalScroll(rememberScrollState()),
        )
        // length and equipment share one quiet, scrollable row under the category switch
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SegmentedPill(
                options = DurationFilter.entries.map { it.label },
                selectedIndex = DurationFilter.entries.indexOf(filter.duration),
                onSelect = { onDuration(DurationFilter.entries[it]) },
                accent = MfColors.Ink,
                compact = true,
            )
            SegmentedPill(
                options = EquipmentFilter.entries.map { it.label },
                selectedIndex = EquipmentFilter.entries.indexOf(filter.equipment),
                onSelect = { onEquipment(EquipmentFilter.entries[it]) },
                accent = MfColors.Ink,
                compact = true,
            )
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
                        val groups = visible.groupBy { it.category }
                        groups.forEach { (category, lessons) ->
                            Column {
                                SectionHeader(
                                    if (category == TrainingCategory.FIGHTING_FUNDAMENTALS) "Fighting" else category.displayName,
                                    trailing = "${lessons.size} lesson${if (lessons.size == 1) "" else "s"}",
                                    trailingColor = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                Spacer(Modifier.height(4.dp))
                                lessons.forEachIndexed { i, ex ->
                                    if (i > 0) ThinRule()
                                    LessonLine(ex, coach, onOpenLesson)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LessonLine(exercise: Exercise, coach: Coach, onOpenLesson: (String) -> Unit) {
    val note = buildList {
        add(exercise.level.displayName)
        if (exercise.needsEquipment) add(exercise.equipment.first().substringBefore(" (").replaceFirstChar { it.uppercase() })
        else add("No equipment")
    }.joinToString(", ")
    LessonRow(
        title = exercise.name,
        note = note,
        length = formatClock(exercise.durationSeconds),
        accent = exercise.category.accent,
        artPath = coach.lessonArt(exercise.id),
        onClick = { onOpenLesson(exercise.id) },
    )
}
