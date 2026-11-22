package eu.motionforge.app.feature.home

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import eu.motionforge.app.core.design.HeavyRule
import eu.motionforge.app.core.design.ThinRule
import eu.motionforge.app.core.design.LessonRow
import eu.motionforge.app.core.design.MfType
import eu.motionforge.app.core.design.PrimaryButton
import eu.motionforge.app.core.design.StageFloor
import eu.motionforge.app.core.design.onAccent
import eu.motionforge.app.core.design.formatClock
import androidx.compose.ui.text.font.FontWeight
import java.time.format.DateTimeFormatter
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
    val side = Modifier.padding(horizontal = 20.dp)
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        // masthead: the date, set like the top line of a printed programme
        Row(Modifier.padding(start = 20.dp, end = 20.dp, top = 16.dp), verticalAlignment = Alignment.Bottom) {
            val today = remember { LocalDate.now() }
            Text(
                today.format(DateTimeFormatter.ofPattern("EEEE d MMMM", Locale.getDefault())),
                style = MaterialTheme.typography.titleSmall,
                modifier = Modifier.weight(1f),
            )
            Text("MOTIONFORGE", style = MaterialTheme.typography.labelLarge.copy(fontFamily = eu.motionforge.app.core.design.DisplayFont, fontWeight = FontWeight.Black))
        }

        if (unfinished != null) Box(side) { UnfinishedCard(unfinished, onResumeUnfinished, onDiscardUnfinished) }

        when (catalog) {
            CatalogUiState.Loading -> Row(side, verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp, color = MfColors.Ink)
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
                    TodayField(quick, coach, onStartQuickSession)
                    Programme(quick, side)
                    Box(side) { PrimaryButton("Start session", onClick = onStartQuickSession, trailing = formatClock(quick.totalSeconds)) }
                } else {
                    Panel(side) { Text("No lessons are available in this build.") }
                }

                Box(side) { WeekStrip(trainedDaysThisWeek, sessionsThisWeek) }

                Box(side) { SectionHeader("Lessons") }
                Row(side, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    TrainingCategory.entries.forEach { category ->
                        val inCategory = exercises.filter { it.category == category }
                        if (inCategory.isNotEmpty()) {
                            CategoryField(category, inCategory, coach, Modifier.weight(1f)) { onOpenCategory(category) }
                        }
                    }
                }

                val lastViewed = exercises.firstOrNull { it.id == preferences.lastViewedExerciseId }
                val suggestion = LessonSuggestions.suggest(exercises, preferences.focus, preferences.goal, preferences.lastViewedExerciseId)
                val picks = listOfNotNull(
                    lastViewed?.let { "Pick up where you left off" to it },
                    suggestion?.takeIf { it != lastViewed }?.let { "Suggested for your goal" to it },
                )
                if (picks.isNotEmpty()) {
                    Column(side) {
                        SectionHeader("For you")
                        Spacer(Modifier.height(6.dp))
                        picks.forEachIndexed { i, (note, ex) ->
                            if (i > 0) ThinRule()
                            LessonRow(ex.name, note, formatClock(ex.durationSeconds), ex.category.accent, coach.lessonArt(ex.id), { onOpenLesson(ex.id) })
                        }
                    }
                }
            }
        }

        Column(side.padding(top = 18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            ThinRule()
            Text("Train safely", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(top = 8.dp))
            Text(
                "Train in clear space, at your own pace. Stop if you feel pain, dizziness or unusual discomfort. " +
                    "MOTIONFORGE does not replace a qualified trainer or instructor.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/**
 * The signature block: today's session as a full-width field of its colour, the length in huge narrow numerals, the
 * coach standing in the field and the session's name in the wide face. Tapping anywhere starts it.
 */
@Composable
private fun TodayField(plan: SessionPlan, coach: Coach, onStart: () -> Unit) {
    val field = plan.type.accent
    val on = plan.type.onAccent
    val minutes = (plan.totalSeconds + 30) / 60
    val moves = plan.steps.filterIsInstance<SessionStep.Work>()
    Box(
        Modifier
            .fillMaxWidth()
            .height(470.dp)
            .background(field)
            .clickable(onClick = onStart)
            .semantics {
                role = Role.Button
                contentDescription = "Start today's session: ${plan.title}, about $minutes minutes, ${moves.size} moves"
            },
    ) {
        StageFloor(field, Modifier.align(Alignment.BottomEnd).width(240.dp).padding(bottom = 4.dp))
        CoachArt(coach.heroArt, Modifier.align(Alignment.BottomEnd).fillMaxHeight(0.9f).width(230.dp).padding(end = 4.dp, bottom = 6.dp))
        Column(Modifier.align(Alignment.TopStart).padding(start = 20.dp, top = 18.dp)) {
            Text("Today", style = MaterialTheme.typography.titleMedium, color = on)
            Row(verticalAlignment = Alignment.Bottom) {
                Text("$minutes", style = MfType.NumeralHuge, color = on)
                Text(
                    "min",
                    style = MaterialTheme.typography.headlineSmall,
                    color = on,
                    modifier = Modifier.padding(start = 6.dp, bottom = 18.dp),
                )
            }
            Text("${moves.size} moves", style = MaterialTheme.typography.titleMedium, color = on)
        }
        Text(
            plan.title,
            style = MaterialTheme.typography.displaySmall,
            color = on,
            modifier = Modifier.align(Alignment.BottomStart).fillMaxWidth(0.62f).padding(start = 20.dp, bottom = 22.dp),
        )
    }
}

/** Today's moves as numbered lines with their times, like a workout card. */
@Composable
private fun Programme(plan: SessionPlan, modifier: Modifier) {
    val work = plan.steps.filterIsInstance<SessionStep.Work>()
    Column(modifier) {
        work.forEachIndexed { i, step ->
            if (i > 0) ThinRule()
            Row(Modifier.padding(vertical = 11.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("${i + 1}", style = MfType.NumeralSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(36.dp))
                Text(step.name, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Text(formatClock(step.durationSeconds), style = MaterialTheme.typography.titleSmall)
            }
        }
    }
}

/** A category as a tall field of its colour with the coach mid-move; opens the lesson list. */
@Composable
private fun CategoryField(category: TrainingCategory, lessons: List<Exercise>, coach: Coach, modifier: Modifier, onClick: () -> Unit) {
    val on = category.onAccent
    val art = when (category) {
        TrainingCategory.FITNESS -> lessons.firstOrNull { it.id.contains("squat") } ?: lessons.first()
        TrainingCategory.FIGHTING_FUNDAMENTALS -> lessons.firstOrNull { it.id.contains("cross") } ?: lessons.first()
    }
    Box(
        modifier
            .height(250.dp)
            .background(category.accent)
            .clickable(onClick = onClick)
            .semantics { role = Role.Button; contentDescription = "${category.displayName}, ${lessons.size} lessons" },
    ) {
        CoachArt(coach.lessonArt(art.id), Modifier.fillMaxSize().padding(top = 56.dp, bottom = 4.dp))
        Column(Modifier.padding(14.dp)) {
            Text(if (category == TrainingCategory.FIGHTING_FUNDAMENTALS) "Fighting" else category.displayName, style = MaterialTheme.typography.headlineSmall, color = on)
            Text("${lessons.size} lessons", style = MaterialTheme.typography.labelLarge, color = on)
        }
    }
}

/** Mon–Sun as seven blocks, filled black on days you trained. Labelled per day, so it's not colour-only. */
@Composable
private fun WeekStrip(trained: Set<DayOfWeek>, sessionsThisWeek: Int?) {
    val today = remember { LocalDate.now().dayOfWeek }
    Column(Modifier.fillMaxWidth()) {
        SectionHeader(
            "This week",
            trailing = when (sessionsThisWeek) {
                null -> null
                0 -> "No sessions yet"
                1 -> "1 session"
                else -> "$sessionsThisWeek sessions"
            },
        )
        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            DayOfWeek.values().forEach { d ->
                val done = d in trained
                val name = d.getDisplayName(TextStyle.SHORT, Locale.getDefault())
                Column(
                    Modifier.weight(1f).semantics(mergeDescendants = true) { contentDescription = "$name: " + if (done) "trained" else "no session" },
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .height(34.dp)
                            .background(if (done) MfColors.Ink else Color.Transparent)
                            .then(if (!done) Modifier.border(if (d == today) 3.dp else 1.dp, if (d == today) MfColors.Ink else MfColors.Rule) else Modifier),
                    )
                    Text(
                        name.take(2),
                        style = MaterialTheme.typography.labelMedium,
                        color = if (d == today) MfColors.Ink else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun UnfinishedCard(snap: SessionSnapshot, onResume: (SessionSnapshot) -> Unit, onDiscard: () -> Unit) {
    val st = snap.state
    val finished = st.phase == SessionPhase.FINISHED
    Surface(
        shape = RoundedCornerShape(2.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        border = BorderStroke(3.dp, MfColors.Ink),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Eyebrow(if (finished) "Workout not saved yet" else "Unfinished workout")
            Text(st.plan.title, style = MaterialTheme.typography.headlineSmall)
            Text(
                if (finished) "You finished it, but the app closed before saving."
                else "${st.results.size} of ${st.plan.workCount} exercises done. Paused when the app closed.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 6.dp)) {
                androidx.compose.material3.Button(onClick = { onResume(snap) }, shape = RoundedCornerShape(2.dp)) { Text(if (finished) "Review and save" else "Resume") }
                OutlinedButton(onClick = { onDiscard() }, shape = RoundedCornerShape(2.dp)) { Text("Discard") }
            }
        }
    }
}
