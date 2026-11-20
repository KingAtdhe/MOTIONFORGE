package eu.motionforge.app.feature.home

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import eu.motionforge.app.core.design.CoachArt
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.LessonTile
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.SectionHeader
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.design.formatLength
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.catalog.CatalogUiState
import eu.motionforge.app.feature.catalog.LessonSuggestions
import eu.motionforge.app.feature.session.SessionPhase
import eu.motionforge.app.feature.session.SessionPlan
import eu.motionforge.app.feature.session.SessionPlanner
import eu.motionforge.app.feature.session.SessionSnapshot
import eu.motionforge.app.feature.session.SessionStep
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.TextStyle
import java.util.Locale

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
    trainedDaysThisWeek: Set<DayOfWeek> = emptySet(),
) {
    val coach = preferences.coach
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Column(Modifier.padding(horizontal = 4.dp, vertical = 8.dp)) {
            val hour = remember { LocalTime.now().hour }
            Text(
                when (hour) {
                    in 5..11 -> "Good morning"
                    in 12..17 -> "Good afternoon"
                    else -> "Good evening"
                },
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text("Ready to move?", style = MaterialTheme.typography.headlineLarge, modifier = Modifier.semantics { heading() })
        }

        if (unfinished != null) UnfinishedCard(unfinished, onResumeUnfinished, onDiscardUnfinished)

        when (catalog) {
            CatalogUiState.Loading -> Row(Modifier.padding(4.dp), verticalAlignment = Alignment.CenterVertically) {
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
                if (quick != null) {
                    TodayStage(quick, coach, onStartQuickSession)
                } else {
                    Panel { Text("No lessons are available in this build.") }
                }

                WeekStrip(trainedDaysThisWeek, sessionsThisWeek)

                val lastViewed = exercises.firstOrNull { it.id == preferences.lastViewedExerciseId }
                val suggestion = LessonSuggestions.suggest(exercises, preferences.focus, preferences.goal, preferences.lastViewedExerciseId)
                val picks = listOfNotNull(lastViewed?.let { "Continue" to it }, suggestion?.takeIf { it != lastViewed }?.let { "Suggested" to it })
                if (picks.isNotEmpty()) {
                    SectionHeader("For you")
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        picks.forEach { (label, ex) -> HomeTile(ex, coach, onOpenLesson, label) }
                    }
                }

                TrainingCategory.entries.forEach { category ->
                    val inCategory = exercises.filter { it.category == category }
                    if (inCategory.isNotEmpty()) {
                        SectionHeader(category.displayName, trailing = "See all", trailingColor = category.accent, onTrailing = { onOpenCategory(category) })
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            inCategory.forEach { HomeTile(it, coach, onOpenLesson) }
                        }
                    }
                }
            }
        }

        Panel {
            Eyebrow("Train safely", color = MfColors.Caution)
            Text(
                "Train in clear space, at your own pace. Stop if you feel pain, dizziness or unusual discomfort. " +
                    "MOTIONFORGE does not replace a qualified trainer or instructor.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Spacer(Modifier.height(8.dp))
    }
}

/** The signature block: today's session on a solid colour field, the moves' names huge behind the coach. */
@Composable
private fun TodayStage(plan: SessionPlan, coach: Coach, onStart: () -> Unit) {
    val accent = plan.type.accent
    val minutes = (plan.totalSeconds + 30) / 60
    val moves = plan.steps.filterIsInstance<SessionStep.Work>()
    Surface(
        onClick = onStart,
        modifier = Modifier.fillMaxWidth().height(340.dp).semantics {
            role = Role.Button
            contentDescription = "Start today's session: ${plan.title}, about $minutes minutes, ${moves.size} moves"
        },
        shape = RoundedCornerShape(28.dp),
        color = accent,
    ) {
        Box(Modifier.fillMaxSize()) {
            CoachArt(coach.heroArt, Modifier.align(Alignment.BottomEnd).fillMaxHeight().width(210.dp).padding(top = 14.dp))
            Column(
                Modifier.align(Alignment.BottomStart).fillMaxWidth(0.62f).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text("Today's session", style = MaterialTheme.typography.titleSmall, color = Color.White.copy(alpha = 0.82f))
                Text(plan.title, style = MaterialTheme.typography.headlineMedium, color = Color.White)
                Text(
                    "$minutes min, ${moves.size} moves",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.82f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.height(10.dp))
                Surface(shape = RoundedCornerShape(50), color = Color.White) {
                    Text("Start", Modifier.padding(horizontal = 26.dp, vertical = 11.dp), style = MaterialTheme.typography.titleMedium, color = accent)
                }
            }
        }
    }
}

/** Mon–Sun with the days you trained filled in. Labelled per day, so it's not colour-only; no streak counter. */
@Composable
private fun WeekStrip(trained: Set<DayOfWeek>, sessionsThisWeek: Int?) {
    val today = remember { LocalDate.now().dayOfWeek }
    Surface(shape = RoundedCornerShape(22.dp), color = MaterialTheme.colorScheme.surface, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(horizontal = 18.dp, vertical = 14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("This week", style = MaterialTheme.typography.titleSmall)
                Text(
                    when (sessionsThisWeek) {
                        null -> " "
                        0 -> "No sessions yet"
                        1 -> "1 session"
                        else -> "$sessionsThisWeek sessions"
                    },
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            DayOfWeek.values().forEach { d ->
                val done = d in trained
                val name = d.getDisplayName(TextStyle.SHORT, Locale.getDefault())
                Column(
                    Modifier.padding(start = 6.dp).semantics(mergeDescendants = true) { contentDescription = "$name: " + if (done) "trained" else "no session" },
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Box(
                        Modifier
                            .size(22.dp)
                            .clip(CircleShape)
                            .background(if (done) MfColors.Cobalt else Color.Transparent)
                            .then(if (!done) Modifier.border(2.dp, if (d == today) MfColors.Ink else MfColors.Rule, CircleShape) else Modifier),
                    )
                    Text(name.take(1), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun UnfinishedCard(snap: SessionSnapshot, onResume: (SessionSnapshot) -> Unit, onDiscard: () -> Unit) {
    val st = snap.state
    val finished = st.phase == SessionPhase.FINISHED
    val accent = st.plan.type.accent
    Surface(
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(2.dp, accent),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Eyebrow(if (finished) "Workout not saved yet" else "Unfinished workout", color = accent)
            Text(st.plan.title, style = MaterialTheme.typography.headlineSmall)
            Text(
                if (finished) "You finished it, but the app closed before saving."
                else "${st.results.size} of ${st.plan.workCount} exercises done. Paused when the app closed.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                androidx.compose.material3.Button(onClick = { onResume(snap) }) { Text(if (finished) "Review and save" else "Resume") }
                OutlinedButton(onClick = onDiscard) { Text("Discard") }
            }
        }
    }
}

@Composable
private fun HomeTile(exercise: Exercise, coach: Coach, onOpenLesson: (String) -> Unit, badge: String? = null) {
    LessonTile(
        title = exercise.name,
        meta = formatLength(exercise.durationSeconds),
        accent = exercise.category.accent,
        artPath = coach.lessonArt(exercise.id),
        onClick = { onOpenLesson(exercise.id) },
        modifier = Modifier.width(168.dp),
        badge = badge,
    )
}
