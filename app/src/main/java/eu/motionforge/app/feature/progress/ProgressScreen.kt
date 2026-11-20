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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
    ScreenColumn(title = "Progress") {
        if (history == null) {
            Text("Loading your history…")
            return@ScreenColumn
        }
        val zone = remember { ZoneId.systemDefault() }
        val summary = remember(history) { ProgressStats.summarize(history, LocalDate.now(zone), zone) }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile("${summary.sessionsThisWeek}", "Sessions this week", Modifier.weight(1f), accent = MfColors.Cobalt)
            StatTile("${summary.minutesThisWeek}", "Minutes this week", Modifier.weight(1f))
        }

        WeekDots(summary.trainedDaysThisWeek, LocalDate.now(zone).dayOfWeek)

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
            return@ScreenColumn
        }

        Panel {
            Eyebrow("Last 4 weeks")
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
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (w.sessions > 0) MfColors.Cobalt else MfColors.Rule),
                        )
                        Text(w.weekStart.format(weekFormat), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            Text("${summary.totalSessions} sessions saved in total", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        Eyebrow("History")
        val dateFormat = remember { DateTimeFormatter.ofPattern("EEEE d MMMM, HH:mm") }
        history.forEach { r ->
            Surface(
                shape = RoundedCornerShape(18.dp),
                color = MaterialTheme.colorScheme.surface,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
            ) {
                Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min)) {
                    Box(
                        Modifier
                            .width(84.dp)
                            .fillMaxHeight()
                            .background(Brush.verticalGradient(listOf(Color.Transparent, r.type.accent.copy(alpha = 0.3f)))),
                    ) {
                        r.exercises.firstOrNull()?.let { CoachArt(coach.lessonArt(it.exerciseId), Modifier.fillMaxSize().padding(top = 6.dp)) }
                    }
                    Column(Modifier.padding(14.dp).weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Eyebrow(Instant.ofEpochMilli(r.startedAtMillis).atZone(zone).format(dateFormat), color = r.type.accent)
                        Text(r.title, style = MaterialTheme.typography.titleLarge)
                        val reps = r.exercises.mapNotNull { it.repetitions }
                        val parts = buildList {
                            add(formatClock(r.durationSeconds))
                            add("${r.exercises.size} exercise${if (r.exercises.size == 1) "" else "s"}")
                            if (reps.isNotEmpty()) add("${reps.sum()} reps")
                            r.perceivedEffort?.let { add("effort $it/10") }
                            if (!r.completed) add("ended early")
                        }
                        Text(parts.joinToString(", "), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(r.exercises.joinToString(", ") { it.name }, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}

/** Mon–Sun row: filled when a session was saved that day. Text label per day, so it's not colour-only. */
@Composable
private fun WeekDots(trained: Set<DayOfWeek>, today: DayOfWeek) {
    Panel {
        Eyebrow("This week")
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            DayOfWeek.values().forEach { d ->
                val done = d in trained
                val name = d.getDisplayName(TextStyle.SHORT, Locale.getDefault())
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.semantics(mergeDescendants = true) {
                        contentDescription = "$name: " + if (done) "trained" else "no session"
                    },
                ) {
                    Box(
                        Modifier
                            .size(34.dp)
                            .clip(CircleShape)
                            .background(if (done) MfColors.Cobalt else MfColors.Ground)
                            .then(if (d == today && !done) Modifier.border(2.dp, MfColors.Cobalt, CircleShape) else Modifier),
                        contentAlignment = Alignment.Center,
                    ) {
                        if (done) Text("✓", color = androidx.compose.ui.graphics.Color.White, style = MaterialTheme.typography.titleMedium)
                    }
                    Text(name.take(2), style = MaterialTheme.typography.labelMedium, color = if (d == today) MfColors.Ink else MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
