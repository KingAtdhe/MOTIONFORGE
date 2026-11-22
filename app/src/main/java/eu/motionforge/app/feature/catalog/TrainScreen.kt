package eu.motionforge.app.feature.catalog

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.LessonRow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.PrimaryButton
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.design.SecondaryButton
import eu.motionforge.app.core.design.SectionHeader
import eu.motionforge.app.core.design.SegmentedPill
import eu.motionforge.app.core.design.ThinRule
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.design.formatClock
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory

/**
 * Moves: the lesson contact sheet. Each lesson is a row with four frames of its movement, so you choose by how it
 * moves. Kind sits on top; length and equipment live in a bottom sheet, within thumb reach.
 */
@OptIn(ExperimentalMaterial3Api::class)
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
    var sheet by rememberSaveable { mutableStateOf(false) }
    ScreenColumn(title = "Moves") {
        val categories = listOf<TrainingCategory?>(null) + TrainingCategory.entries
        Row(verticalAlignment = Alignment.CenterVertically) {
            SegmentedPill(
                options = categories.map { it?.let { c -> if (c == TrainingCategory.FIGHTING_FUNDAMENTALS) "Fighting" else c.displayName } ?: "All" },
                selectedIndex = categories.indexOf(filter.category),
                onSelect = { onCategory(categories[it]) },
                modifier = Modifier.weight(1f, fill = false).horizontalScroll(rememberScrollState()),
            )
            Spacer(Modifier.width(8.dp))
            val extra = listOfNotNull(
                filter.duration.takeIf { it != DurationFilter.ANY },
                filter.equipment.takeIf { it != EquipmentFilter.ANY },
            ).size
            TextButton(onClick = { sheet = true }, modifier = Modifier.heightIn(min = 48.dp)) {
                Text(if (extra > 0) "Filters ($extra)" else "Filters", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onBackground)
            }
        }

        when (catalog) {
            CatalogUiState.Loading -> Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp, color = MfColors.Ink)
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
                    else -> visible.groupBy { it.category }.forEach { (category, lessons) ->
                        Column {
                            SectionHeader(
                                if (category == TrainingCategory.FIGHTING_FUNDAMENTALS) "Fighting" else category.displayName,
                                trailing = "${lessons.size} lesson${if (lessons.size == 1) "" else "s"}",
                            )
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

    if (sheet) {
        ModalBottomSheet(onDismissRequest = { sheet = false }, containerColor = MaterialTheme.colorScheme.background) {
            Column(Modifier.padding(horizontal = 16.dp).padding(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("Filters", style = MaterialTheme.typography.headlineMedium)
                Eyebrow("Length")
                SegmentedPill(
                    options = DurationFilter.entries.map { it.label },
                    selectedIndex = DurationFilter.entries.indexOf(filter.duration),
                    onSelect = { onDuration(DurationFilter.entries[it]) },
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    compact = true,
                )
                Eyebrow("Equipment")
                SegmentedPill(
                    options = EquipmentFilter.entries.map { it.label },
                    selectedIndex = EquipmentFilter.entries.indexOf(filter.equipment),
                    onSelect = { onEquipment(EquipmentFilter.entries[it]) },
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    compact = true,
                )
                Spacer(Modifier.height(4.dp))
                PrimaryButton("Show lessons", onClick = { sheet = false })
                SecondaryButton("Clear filters", onClick = { onClearFilters(); sheet = false })
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
        artPath = coach.stripArt(exercise.id),
        onClick = { onOpenLesson(exercise.id) },
    )
}
