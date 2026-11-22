package eu.motionforge.app.feature.home

import androidx.compose.foundation.layout.navigationBarsPadding
import eu.motionforge.app.core.design.WeekTicks
import eu.motionforge.app.core.design.MeasureScale
import eu.motionforge.app.core.design.MotionStudy
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
    val side = Modifier.padding(horizontal = 16.dp)
    val quick = (catalog as? CatalogUiState.Ready)?.let { SessionPlanner.quick(it.exercises, preferences.focus) }
    Box(Modifier.fillMaxSize()) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = if (quick != null) 104.dp else 20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(Modifier.padding(start = 16.dp, end = 16.dp, top = 14.dp), verticalAlignment = Alignment.CenterVertically) {
                val today = remember { LocalDate.now() }
                Text(
                    today.format(DateTimeFormatter.ofPattern("EEEE d MMMM", Locale.getDefault())),
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.weight(1f),
                )
                Text("MOTIONFORGE", style = MaterialTheme.typography.labelLarge.copy(fontFamily = eu.motionforge.app.core.design.DisplayFont, fontWeight = FontWeight.Bold))
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
                    if (quick != null) {
                        TodayPlate(quick, coach, onStartQuickSession, side)
                        Filmstrip(quick, coach, side)
                    } else {
                        Panel(side) { Text("No lessons are available in this build.") }
                    }

                    Column(side) {
                        SectionHeader(
                            "This week",
                            trailing = when (sessionsThisWeek) {
                                null -> null
                                0 -> "No sessions yet"
                                1 -> "1 session"
                                else -> "$sessionsThisWeek sessions"
                            },
                        )
                        Spacer(Modifier.height(8.dp))
                        WeekTicks(trainedDaysThisWeek, remember { LocalDate.now().dayOfWeek })
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
                            picks.forEach { (note, ex) ->
                                LessonRow(ex.name, note, formatClock(ex.durationSeconds), ex.category.accent, coach.stripArt(ex.id), { onOpenLesson(ex.id) })
                            }
                        }
                    }
                    Column(side, verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        SectionHeader("All moves")
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            TrainingCategory.entries.forEach { c ->
                                val n = exercises.count { it.category == c }
                                eu.motionforge.app.core.design.SecondaryButton(
                                    "${if (c == TrainingCategory.FIGHTING_FUNDAMENTALS) "Fighting" else c.displayName}  $n",
                                    onClick = { onOpenCategory(c) },
                                    modifier = Modifier.weight(1f),
                                )
                            }
                        }
                    }
                }
            }

            Column(side.padding(top = 10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Train safely", style = MaterialTheme.typography.titleSmall)
                Text(
                    "Train in clear space, at your own pace. Stop if you feel pain, dizziness or unusual discomfort. " +
                        "MOTIONFORGE does not replace a qualified trainer or instructor.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        // the one action, under the thumb
        if (quick != null) {
            Box(
                Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.background)
                    .padding(horizontal = 16.dp, vertical = 12.dp),
            ) {
                PrimaryButton("Start session", onClick = onStartQuickSession, trailing = formatClock(quick.totalSeconds))
            }
        }
    }
}

/** Today's session: the first move's motion study on a black plate, the session's name and length under it. */
@Composable
private fun TodayPlate(plan: SessionPlan, coach: Coach, onStart: () -> Unit, modifier: Modifier) {
    val minutes = (plan.totalSeconds + 30) / 60
    val moves = plan.steps.filterIsInstance<SessionStep.Work>()
    val first = moves.first()
    Column(
        modifier
            .clickable(onClick = onStart)
            .semantics(mergeDescendants = true) {
                role = Role.Button
                contentDescription = "Start today's session: ${plan.title}, about $minutes minutes, ${moves.size} moves"
            },
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box {
            MotionStudy(coach.studyArt(first.exerciseId), Modifier.fillMaxWidth().height(380.dp))
            Text(
                "Today",
                style = MaterialTheme.typography.labelLarge,
                color = Color.White.copy(alpha = 0.75f),
                modifier = Modifier.padding(14.dp),
            )
            MeasureScale(Modifier.align(Alignment.BottomCenter).padding(horizontal = 14.dp, vertical = 10.dp), color = Color.White.copy(alpha = 0.5f))
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Text(plan.title, style = MaterialTheme.typography.headlineLarge, modifier = Modifier.weight(1f))
            Text("$minutes", style = MfType.Numeral)
            Text(" min", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 8.dp))
        }
    }
}

/** The session's moves as a filmstrip of small plates, numbered in order. */
@Composable
private fun Filmstrip(plan: SessionPlan, coach: Coach, modifier: Modifier) {
    val work = plan.steps.filterIsInstance<SessionStep.Work>()
    // four moves fill the width; a longer session scrolls sideways instead of shrinking the frames
    val fits = work.size <= 4
    Row(
        if (fits) modifier else modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        work.forEachIndexed { i, step ->
            Column(if (fits) Modifier.weight(1f) else Modifier.width(84.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                MotionStudy(coach.studyArt(step.exerciseId), Modifier.fillMaxWidth().height(96.dp), crop = true)
                Text("${i + 1}  ${step.name}", style = MaterialTheme.typography.labelSmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(formatClock(step.durationSeconds), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun UnfinishedCard(snap: SessionSnapshot, onResume: (SessionSnapshot) -> Unit, onDiscard: () -> Unit) {
    val st = snap.state
    val finished = st.phase == SessionPhase.FINISHED
    Surface(
        shape = RoundedCornerShape(6.dp),
        color = MfColors.Yellow,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(if (finished) "Workout not saved yet" else "Unfinished workout", style = MaterialTheme.typography.labelLarge, color = Color.Black)
            Text(st.plan.title, style = MaterialTheme.typography.headlineSmall, color = Color.Black)
            Text(
                if (finished) "You finished it, but the app closed before saving."
                else "${st.results.size} of ${st.plan.workCount} exercises done. Paused when the app closed.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Black,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 6.dp)) {
                androidx.compose.material3.Button(
                    onClick = { onResume(snap) },
                    shape = RoundedCornerShape(6.dp),
                    colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = Color.Black, contentColor = Color.White),
                ) { Text(if (finished) "Review and save" else "Resume") }
                OutlinedButton(
                    onClick = { onDiscard() },
                    shape = RoundedCornerShape(6.dp),
                    border = BorderStroke(1.dp, Color.Black),
                    colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(contentColor = Color.Black),
                ) { Text("Discard") }
            }
        }
    }
}
