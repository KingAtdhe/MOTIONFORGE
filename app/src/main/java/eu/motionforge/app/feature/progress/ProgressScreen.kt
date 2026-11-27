package eu.motionforge.app.feature.progress

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Surface
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import eu.motionforge.app.core.design.CoachArt
import eu.motionforge.app.core.model.Coach
import java.time.DayOfWeek
import java.time.format.TextStyle
import java.util.Locale
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import eu.motionforge.app.core.i18n.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.PrimaryButton
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.design.StatTile
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.design.formatClock
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** [history] is null while loading. */
@Composable
fun ProgressScreen(history: List<SessionRecord>?, coach: Coach, onStartSession: () -> Unit) {
    ScreenColumn(title = "Progress") { ProgressContent(history, coach, onStartSession) }
}

/** Progress as part of a page: this week, the last four weeks and the history contact sheet. */
@Composable
fun androidx.compose.foundation.layout.ColumnScope.ProgressContent(history: List<SessionRecord>?, coach: Coach, onStartSession: () -> Unit) {
    run {
        if (history == null) {
            Text("Loading your history…")
            return
        }
        val zone = remember { ZoneId.systemDefault() }
        val summary = remember(history) { ProgressStats.summarize(history, LocalDate.now(zone), zone) }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile("${summary.sessionsThisWeek}", "Sessions this week", Modifier.weight(1f))
            StatTile("${summary.minutesThisWeek}", "Minutes this week", Modifier.weight(1f))
        }

        eu.motionforge.app.core.design.SectionHeader("This week")
        eu.motionforge.app.core.design.WeekTicks(summary.trainedDaysThisWeek, LocalDate.now(zone).dayOfWeek)

        if (history.isEmpty()) {
            Panel {
                Text("No sessions yet", style = MaterialTheme.typography.titleLarge)
                Text(
                    "Finish a session and save it to see it here. History stays on this phone.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            PrimaryButton("Start a short session", onClick = onStartSession)
            return
        }

        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            eu.motionforge.app.core.design.SectionHeader("Last 4 weeks")
            val max = summary.recentWeeks.maxOf { it.sessions }.coerceAtLeast(1)
            val weekFormat = remember { DateTimeFormatter.ofPattern("d MMM") }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Bottom) {
                summary.recentWeeks.forEach { w ->
                    Column(
                        Modifier.weight(1f).semantics { contentDescription = "Week of ${w.weekStart.format(weekFormat)}: ${w.sessions} sessions" },
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Text("${w.sessions}", style = MaterialTheme.typography.titleMedium)
                        Box(
                            Modifier
                                .fillMaxWidth()
                                .height((8 + 72 * w.sessions / max).dp)
                                
                                .background(if (w.sessions > 0) MfColors.Ink else MfColors.Rule),
                        )
                        Text(w.weekStart.format(weekFormat), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            Text("${summary.totalSessions} sessions saved in total", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        val trends = remember(history) { ProgressStats.repTrends(history) }
        if (trends.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                eu.motionforge.app.core.design.SectionHeader("Reps", trailing = "counted by the camera")
                trends.forEachIndexed { i, t ->
                    if (i > 0) eu.motionforge.app.core.design.ThinRule()
                    RepTrendRow(t)
                }
            }
        }
        val holds = remember(history) { ProgressStats.holdTrends(history) }
        if (holds.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                eu.motionforge.app.core.design.SectionHeader("Holds", trailing = "time in position")
                holds.forEachIndexed { i, t ->
                    if (i > 0) eu.motionforge.app.core.design.ThinRule()
                    RepTrendRow(t, seconds = true)
                }
            }
        }

        eu.motionforge.app.core.design.SectionHeader("History")
        val dateFormat = remember { DateTimeFormatter.ofPattern("EEEE d MMMM, HH:mm") }
        Column {
            history.forEachIndexed { i, r ->
                if (i > 0) eu.motionforge.app.core.design.ThinRule()
                Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                    r.exercises.firstOrNull()?.let {
                        eu.motionforge.app.core.design.MotionStudy(coach.studyArt(it.exerciseId), Modifier.width(64.dp).height(80.dp), crop = true)
                    }
                    Column(Modifier.padding(horizontal = 14.dp).weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(Instant.ofEpochMilli(r.startedAtMillis).atZone(zone).format(dateFormat), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(r.title, style = MaterialTheme.typography.titleLarge)
                        val reps = r.exercises.mapNotNull { it.repetitions }
                        val parts = buildList {
                            add(if (r.exercises.size == 1) "1 exercise" else "${r.exercises.size} exercises")
                            if (reps.isNotEmpty()) add("${reps.sum()} reps")
                            r.perceivedEffort?.let { add("effort $it/10") }
                            if (!r.completed) add("ended early")
                        }
                        Text(parts.joinToString(", "), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(formatClock(r.durationSeconds), style = eu.motionforge.app.core.design.MfType.NumeralSmall)
                }
            }
        }
    }
}


/** One exercise: its last sets as bars (the latest in ink, a new best in yellow), last and best counts. */
@Composable
private fun RepTrendRow(t: RepTrend, seconds: Boolean = false) {
    fun fmt(v: Int) = if (seconds) formatClock(v) else "$v"
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 10.dp)
            .semantics(mergeDescendants = true) {
                contentDescription = if (seconds) "${t.name}: last hold ${t.last} seconds, best ${t.best} seconds" + (if (t.newBest) ", a new best" else "")
                    else "${t.name}: last ${t.last} reps, best ${t.best}" + if (t.newBest) ", a new best" else ""
            },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(t.name, style = MaterialTheme.typography.titleMedium)
            Text(
                if (t.newBest) "New best" else "Best ${fmt(t.best)}",
                style = MaterialTheme.typography.labelMedium,
                color = if (t.newBest) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Row(Modifier.height(40.dp).width(96.dp), horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.Bottom) {
            t.recent.forEachIndexed { i, r ->
                val latest = i == t.recent.lastIndex
                Box(
                    Modifier
                        .weight(1f)
                        .height((6 + 34 * r / t.best.coerceAtLeast(1)).dp)
                        .background(
                            when {
                                latest && t.newBest -> MfColors.Yellow
                                latest -> MfColors.Ink
                                else -> MfColors.Rule
                            },
                        ),
                )
            }
        }
        Spacer(Modifier.width(12.dp))
        Text(fmt(t.last), style = eu.motionforge.app.core.design.MfType.NumeralSmall)
    }
}
