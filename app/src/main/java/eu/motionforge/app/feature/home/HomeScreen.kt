package eu.motionforge.app.feature.home

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.CoachArt
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.LessonTile
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.SectionHeader
import eu.motionforge.app.core.design.StatTile
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.catalog.CatalogUiState
import eu.motionforge.app.feature.catalog.LessonSuggestions
import eu.motionforge.app.feature.session.SessionPhase
import eu.motionforge.app.feature.session.SessionPlan
import eu.motionforge.app.feature.session.SessionSnapshot
import eu.motionforge.app.feature.session.SessionPlanner
import eu.motionforge.app.feature.session.SessionStep

@Composable
fun HomeScreen(
    preferences: UserPreferences,
    catalog: CatalogUiState,
    onOpenLesson: (String) -> Unit,
    onOpenCategory: (TrainingCategory) -> Unit,
    onStartQuickSession: () -> Unit,
    sessionsThisWeek: Int?,
    onRetry: () -> Unit,
    unfinished: SessionSnapshot? = null,
    onResumeUnfinished: (SessionSnapshot) -> Unit = {},
    onDiscardUnfinished: () -> Unit = {},
) {
    val coach = preferences.coach
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Column {
            Eyebrow("MOTIONFORGE", color = MaterialTheme.colorScheme.primary)
            Text("READY TO MOVE?", style = MaterialTheme.typography.headlineLarge, modifier = Modifier.semantics { heading() })
            val focusText = preferences.focus?.displayName ?: "All lessons"
            val goalText = preferences.goal?.displayName
            Text(
                if (goalText != null) "$focusText · $goalText" else focusText,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        if (unfinished != null) UnfinishedCard(unfinished, onResumeUnfinished, onDiscardUnfinished)

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
                val quick = SessionPlanner.quick(exercises, preferences.focus)
                val accent = (preferences.focus ?: TrainingCategory.FITNESS).accent
                if (quick != null) {
                    TodayHero(quick, coach, accent, onStartQuickSession)
                } else {
                    Panel { Text("No lessons are available in this build.") }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    StatTile(sessionsThisWeek?.toString() ?: "–", "Sessions this week", Modifier.weight(1f), accent = accent)
                    StatTile(exercises.size.toString(), "Lessons", Modifier.weight(1f))
                }

                val lastViewed = exercises.firstOrNull { it.id == preferences.lastViewedExerciseId }
                val suggestion = LessonSuggestions.suggest(exercises, preferences.focus, preferences.goal, preferences.lastViewedExerciseId)
                val picks = listOfNotNull(lastViewed?.let { "Continue" to it }, suggestion?.let { "Suggested" to it })
                if (picks.isNotEmpty()) {
                    SectionHeader("For you")
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        picks.forEach { (label, ex) -> HomeTile(ex, coach, onOpenLesson, label) }
                    }
                }

                TrainingCategory.entries.forEach { category ->
                    val inCategory = exercises.filter { it.category == category }
                    if (inCategory.isNotEmpty()) {
                        CategoryHeader(category, inCategory.size, onOpenCategory)
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            inCategory.forEach { HomeTile(it, coach, onOpenLesson) }
                        }
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
private fun TodayHero(plan: SessionPlan, coach: Coach, accent: Color, onStart: () -> Unit) {
    val minutes = (plan.totalSeconds + 30) / 60
    Surface(
        onClick = onStart,
        modifier = Modifier.fillMaxWidth().height(300.dp).semantics { role = Role.Button },
        shape = RoundedCornerShape(26.dp),
        color = MfColors.Panel,
        border = BorderStroke(1.dp, accent.copy(alpha = 0.5f)),
    ) {
        Box(
            Modifier
                .fillMaxSize()
                .background(Brush.linearGradient(listOf(accent.copy(alpha = 0.38f), MfColors.Panel, MfColors.Ink))),
        ) {
            // coach portrait on the right, behind the text
            CoachArt(
                coach.heroArt,
                Modifier.align(Alignment.BottomEnd).fillMaxHeight().width(190.dp).padding(top = 10.dp),
                contentScale = ContentScale.Fit,
            )
            Box(
                Modifier
                    .fillMaxSize()
                    .background(Brush.horizontalGradient(0f to MfColors.Ink.copy(alpha = 0.55f), 0.6f to Color.Transparent)),
            )
            Column(
                Modifier.fillMaxHeight().fillMaxWidth(0.62f).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Eyebrow("Today · about $minutes min", color = accent)
                Text(plan.title.uppercase(), style = MaterialTheme.typography.headlineLarge)
                Text(
                    plan.steps.filterIsInstance<SessionStep.Work>().joinToString(" → ") { it.name },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MfColors.Chalk.copy(alpha = 0.8f),
                    maxLines = 4,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(50), color = accent) {
                    Text(
                        "▶  START",
                        Modifier.padding(horizontal = 22.dp, vertical = 12.dp),
                        style = MaterialTheme.typography.titleLarge,
                        color = MfColors.Ink,
                    )
                }
            }
        }
    }
}

@Composable
private fun CategoryHeader(category: TrainingCategory, count: Int, onOpenCategory: (TrainingCategory) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(4.dp).height(22.dp).background(category.accent, RoundedCornerShape(2.dp)))
        Spacer(Modifier.width(10.dp))
        Text(category.displayName.uppercase(), style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f).semantics { heading() })
        androidx.compose.material3.TextButton(onClick = { onOpenCategory(category) }) {
            Text("All $count  ›", color = category.accent)
        }
    }
}

@Composable
private fun HomeTile(exercise: Exercise, coach: Coach, onOpenLesson: (String) -> Unit, eyebrow: String? = null) {
    LessonTile(
        title = exercise.name,
        meta = "${exercise.durationSeconds} s · ${exercise.level.displayName}",
        accent = exercise.category.accent,
        artPath = coach.lessonArt(exercise.id),
        onClick = { onOpenLesson(exercise.id) },
        modifier = Modifier.width(170.dp),
        eyebrow = eyebrow,
    )
}

@Composable
private fun UnfinishedCard(snap: SessionSnapshot, onResume: (SessionSnapshot) -> Unit, onDiscard: () -> Unit) {
    val st = snap.state
    val finished = st.phase == SessionPhase.FINISHED
    val accent = st.plan.type.accent
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = MfColors.PanelRaised,
        border = BorderStroke(1.dp, accent),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Eyebrow(if (finished) "Workout not saved yet" else "Unfinished workout", color = accent)
            Text(st.plan.title.uppercase(), style = MaterialTheme.typography.titleLarge)
            val done = st.results.size
            Text(
                if (finished) "You finished it but the app closed before saving."
                else "$done of ${st.plan.workCount} exercises done · paused when the app closed.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                androidx.compose.material3.Button(onClick = { onResume(snap) }) { Text(if (finished) "Review & save" else "Resume") }
                OutlinedButton(onClick = onDiscard) { Text("Discard") }
            }
        }
    }
}
