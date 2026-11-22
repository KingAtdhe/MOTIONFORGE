package eu.motionforge.app.feature.home

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import eu.motionforge.app.core.design.stageBrush
import eu.motionforge.app.core.design.StageFloor
import eu.motionforge.app.core.design.KindMark
import androidx.compose.foundation.clickable
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
            .padding(bottom = 12.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        val side = Modifier.padding(horizontal = 20.dp)
        Column(Modifier.padding(start = 20.dp, end = 20.dp, top = 18.dp)) {
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
            Text("Ready to move?", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onBackground, modifier = Modifier.semantics { heading() })
        }

        if (unfinished != null) Box(side) { UnfinishedCard(unfinished, onResumeUnfinished, onDiscardUnfinished) }

        when (catalog) {
            CatalogUiState.Loading -> Row(side, verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp)
                Spacer(Modifier.width(12.dp))
                Text("Loading lessons…")
            }
            is CatalogUiState.Error -> Panel(side) {
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
                    Panel(side) { Text("No lessons are available in this build.") }
                }

                Box(side) { WeekStrip(trainedDaysThisWeek, sessionsThisWeek) }

                val lastViewed = exercises.firstOrNull { it.id == preferences.lastViewedExerciseId }
                val suggestion = LessonSuggestions.suggest(exercises, preferences.focus, preferences.goal, preferences.lastViewedExerciseId)
                val picks = listOfNotNull(lastViewed?.let { "Continue" to it }, suggestion?.takeIf { it != lastViewed }?.let { "Suggested" to it })
                if (picks.isNotEmpty()) {
                    Box(side) { SectionHeader("For you") }
                    Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        picks.forEach { (label, ex) -> HomeTile(ex, coach, onOpenLesson, label) }
                    }
                }

                TrainingCategory.entries.forEach { category ->
                    val inCategory = exercises.filter { it.category == category }
                    if (inCategory.isNotEmpty()) {
                        Box(side) { SectionHeader(category.displayName, trailing = "See all", onTrailing = { onOpenCategory(category) }) }
                        Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            inCategory.forEach { HomeTile(it, coach, onOpenLesson) }
                        }
                    }
                }
            }
        }

        Panel(side) {
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

/**
 * The signature block: today's session as an edge-to-edge studio shot of the coach, with the session's name set large in
 * the extra-wide face across the lower part of the picture, like a training poster. One tap starts it.
 */
@Composable
private fun TodayStage(plan: SessionPlan, coach: Coach, onStart: () -> Unit) {
    val accent = plan.type.accent
    val minutes = (plan.totalSeconds + 30) / 60
    val moves = plan.steps.filterIsInstance<SessionStep.Work>()
    Box(
        Modifier
            .fillMaxWidth()
            .height(480.dp)
            .background(stageBrush(accent))
            .clickable(onClick = onStart)
            .semantics {
                role = Role.Button
                contentDescription = "Start today's session: ${plan.title}, about $minutes minutes, ${moves.size} moves"
            },
    ) {
        StageFloor(accent, Modifier.align(Alignment.BottomCenter).padding(bottom = 150.dp))
        CoachArt(coach.heroArt, Modifier.align(Alignment.TopEnd).fillMaxHeight(0.86f).width(250.dp).padding(top = 16.dp, end = 8.dp))
        // the type sits over the coach's legs; a short fade keeps it readable without boxing it in
        Box(
            Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(230.dp)
                .background(androidx.compose.ui.graphics.Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(alpha = 0.72f)))),
        )
        Column(Modifier.align(Alignment.BottomStart).padding(start = 20.dp, end = 20.dp, bottom = 22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Today", style = MaterialTheme.typography.labelLarge, color = Color.White.copy(alpha = 0.72f))
            Text(plan.title, style = MaterialTheme.typography.displayMedium, color = Color.White)
            Row(verticalAlignment = Alignment.CenterVertically) {
                KindMark(accent)
                Spacer(Modifier.width(8.dp))
                Text("$minutes min, ${moves.size} moves", style = MaterialTheme.typography.bodyMedium, color = Color.White.copy(alpha = 0.8f))
                Spacer(Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(50), color = Color.White) {
                    Text("Start session", Modifier.padding(horizontal = 20.dp, vertical = 12.dp), style = MaterialTheme.typography.titleSmall, color = Color.Black)
                }
            }
        }
    }
}

/** Mon–Sun with the days you trained filled in. Labelled per day, so it's not colour-only; no streak counter. */
@Composable
private fun WeekStrip(trained: Set<DayOfWeek>, sessionsThisWeek: Int?) {
    val today = remember { LocalDate.now().dayOfWeek }
    Surface(color = Color.Transparent, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
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
                            .size(18.dp)
                            .clip(CircleShape)
                            .background(if (done) MfColors.Ink else Color.Transparent)
                            .then(if (!done) Modifier.border(1.5.dp, if (d == today) MfColors.Ink else MfColors.Rule, CircleShape) else Modifier),
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
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surface,
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
        modifier = Modifier.width(176.dp),
        artHeight = 220.dp,
        badge = badge,
    )
}
