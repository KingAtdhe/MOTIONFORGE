package eu.motionforge.app.feature.lesson

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import eu.motionforge.app.core.design.formatLength
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import eu.motionforge.app.core.design.accent
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import eu.motionforge.app.core.i18n.Text
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
import eu.motionforge.app.core.design.PrimaryButton
import eu.motionforge.app.feature.session.SessionPlanner
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
    onStartPractice: (String) -> Unit,
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
                LessonDetail(exercise, onBack, onStartPractice)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun LessonDetail(exercise: Exercise, onBack: () -> Unit, onStartPractice: (String) -> Unit) {
    val appContext = androidx.compose.ui.platform.LocalContext.current.applicationContext
    val prefsFlow = androidx.compose.runtime.remember { (appContext as eu.motionforge.app.MotionForgeApplication).container.preferences.preferences }
    val coach = prefsFlow.collectAsState(initial = null).value?.coach ?: eu.motionforge.app.core.model.Coach.DEFAULT
    var study by androidx.compose.runtime.saveable.rememberSaveable { androidx.compose.runtime.mutableStateOf(false) }
    Box(Modifier.fillMaxSize()) {
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 104.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Box {
            if (study) {
                eu.motionforge.app.core.design.MotionStudy(
                    coach.studyArt(exercise.id),
                    Modifier.fillMaxWidth().height(460.dp),
                    description = "Motion study of ${exercise.name}: several moments of the movement on one picture",
                )
            } else {
                TrainerDemo(exercise)
            }
            androidx.compose.material3.IconButton(onClick = onBack, modifier = Modifier.padding(4.dp)) {
                androidx.compose.material3.Icon(
                    androidx.compose.material.icons.Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = eu.motionforge.app.core.i18n.tr("Back"),
                    tint = androidx.compose.ui.graphics.Color.White,
                )
            }
            eu.motionforge.app.core.design.SegmentedPill(
                options = listOf("3D coach", "Motion study"),
                selectedIndex = if (study) 1 else 0,
                onSelect = { study = it == 1 },
                modifier = Modifier.align(Alignment.TopEnd).padding(10.dp),
                compact = true,
            )
        }
        Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(exercise.name, style = MaterialTheme.typography.displaySmall, modifier = Modifier.semantics { heading() })
            Text(exercise.purpose, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Column {
            eu.motionforge.app.core.design.MeasureScale()
            Row(Modifier.padding(top = 10.dp)) {
                LessonFact(eu.motionforge.app.core.design.formatClock(exercise.durationSeconds), "Length", Modifier.weight(1f))
                LessonFact(exercise.level.displayName, "Level", Modifier.weight(1f))
                LessonFact(exercise.recommendedView.displayName, "Camera view", Modifier.weight(1f))
            }
        }

        if (exercise.reviewStatus == ReviewStatus.DRAFT_PENDING_COACH_REVIEW) {
            Text(
                "Draft lesson: steps and demonstration are pending review by a qualified coach. Use them as a guide, not as a technique standard.",
                style = MaterialTheme.typography.bodySmall,
                color = MfColors.Caution,
            )
        }

        Panel {
            Eyebrow("Safety")
            Text(exercise.safety, style = MaterialTheme.typography.bodyMedium)
        }

        Panel {
            Eyebrow("Space and equipment")
            Text(exercise.space, style = MaterialTheme.typography.bodyMedium)
            Text(
                if (exercise.equipment.isEmpty()) "No equipment needed." else exercise.equipment.joinToString(", "),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        SectionTitle("How to do it")
        Column {
            exercise.instructions.forEachIndexed { i, step ->
                if (i > 0) androidx.compose.material3.HorizontalDivider(color = MaterialTheme.colorScheme.outline)
                Row(Modifier.padding(vertical = 14.dp), verticalAlignment = Alignment.Top) {
                    Text("${i + 1}", style = eu.motionforge.app.core.design.MfType.NumeralSmall, modifier = Modifier.width(40.dp))
                    Text(step, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 2.dp))
                }
            }
        }

        if (exercise.commonCues.isNotEmpty()) {
            SectionTitle("Keep in mind")
            exercise.commonCues.forEach { Text(it, style = MaterialTheme.typography.bodyLarge) }
        }

        if (exercise.commonMistakes.isNotEmpty()) {
            SectionTitle("Common mistakes")
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                exercise.commonMistakes.forEach { m ->
                    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text(m.mistake, style = MaterialTheme.typography.titleMedium)
                        Text(m.adjustment, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        Panel {
            Eyebrow("Camera feedback")
            Text(exercise.analysisMode.displayName, style = MaterialTheme.typography.titleMedium)
            Text(exercise.limitations, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                if (eu.motionforge.app.core.movement.CountedMove.forExercise(exercise.id) != null) {
                    "In practice with the camera on, repetitions are counted automatically, and a few simple form rules may suggest an adjustment. This is experimental — it does not judge safety."
                } else if (eu.motionforge.app.core.movement.HoldCheck.forExercise(exercise.id) != null) {
                    "In practice with the camera on, it times your hold only while you're in the position, and a simple rule may suggest an adjustment. This is experimental — it does not judge safety."
                } else if (SessionPlanner.drillFor(exercise.id) != null) {
                    "In practice with the camera on, it watches your guard and feet and suggests simple adjustments. This is experimental."
                } else {
                    "In practice, the camera works as a mirror with a tracking skeleton. It does not assess this movement yet."
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        }
    }
    Box(
        Modifier
            .align(Alignment.BottomCenter)
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.background)
            .padding(horizontal = 16.dp, vertical = 12.dp),
    ) {
        PrimaryButton("Start practice", onClick = { onStartPractice(exercise.id) }, trailing = eu.motionforge.app.core.design.formatClock(exercise.durationSeconds))
    }
    }
}

@Composable
private fun LessonFact(value: String, label: String, modifier: Modifier) {
    Column(modifier) {
        Text(value, style = MaterialTheme.typography.titleLarge)
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SectionTitle(text: String) {
    eu.motionforge.app.core.design.SectionHeader(text)
}
