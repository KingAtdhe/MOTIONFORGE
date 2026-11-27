package eu.motionforge.app.feature.progress

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.background
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import eu.motionforge.app.core.design.DisplayFont
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.MfType
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.i18n.Text
import eu.motionforge.app.core.i18n.tr
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** This week against the weekly goal, and the streak of weeks that reached it. Never a warning, never guilt. */
@Composable
fun WeeklyGoalPanel(s: WeekStreak) {
    Panel {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("Weekly goal", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("${minOf(s.doneThisWeek, 99)} of ${s.goal} sessions", style = MaterialTheme.typography.titleLarge)
                Text(
                    when {
                        s.metThisWeek -> "Goal reached this week."
                        s.toGo == 1 -> "1 more session reaches this week's goal."
                        else -> "${s.toGo} more sessions reach this week's goal."
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Column(horizontalAlignment = Alignment.End, modifier = Modifier.semantics(mergeDescendants = true) {}) {
                Text("${s.current}", style = MfType.Numeral)
                Text(if (s.current == 1) "week in a row" else "weeks in a row", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        // one segment per goal session: filled as they're done, all yellow once the goal is reached
        Row(
            Modifier.fillMaxWidth().height(10.dp).clearAndSetSemantics { },
            horizontalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            repeat(s.goal) { i ->
                val filled = i < s.doneThisWeek
                Box(
                    Modifier.weight(1f).height(10.dp).background(
                        when {
                            filled && s.metThisWeek -> MfColors.Yellow
                            filled -> MfColors.Ink
                            else -> MfColors.Rule
                        },
                    ),
                )
            }
        }
        if (s.best > s.current) {
            Text("Best: ${s.best} weeks in a row", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/** Every badge, earned first (newest first), then the ones still to earn, three to a row. */
@Composable
fun BadgeGrid(earned: List<EarnedBadge>, zone: ZoneId) {
    val got = earned.associate { it.badge to it.atMillis }
    val order = earned.sortedByDescending { it.atMillis }.map { it.badge } + Badge.entries.filter { it !in got }
    val dateFormat = DateTimeFormatter.ofPattern("d MMM yyyy")
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        order.chunked(3).forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                row.forEach { b ->
                    val at = got[b]
                    val description = if (at != null) {
                        tr("${b.title}, earned ${Instant.ofEpochMilli(at).atZone(zone).format(dateFormat)}. ${b.detail}")
                    } else {
                        tr("${b.title}, not earned yet. ${b.detail}")
                    }
                    Column(
                        Modifier.weight(1f).clearAndSetSemantics { contentDescription = description },
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Medal(b.mark, earned = at != null)
                        Text(
                            b.title, style = MaterialTheme.typography.labelLarge, textAlign = TextAlign.Center,
                            color = if (at != null) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            b.detail, style = MaterialTheme.typography.labelSmall, textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 3,
                        )
                    }
                }
                repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
            }
        }
    }
}

/** A round medal: earned = timing yellow with an ink ring; still to earn = an outline. */
@Composable
fun Medal(mark: String, earned: Boolean, diameter: Int = 64) {
    Box(Modifier.size(diameter.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(diameter.dp)) {
            val r = this.size.minDimension / 2f
            val c = Offset(r, r)
            if (earned) {
                drawCircle(MfColors.Yellow, r, c)
                drawCircle(MfColors.Ink, r - 3.dp.toPx(), c, style = Stroke(2.dp.toPx()))
            } else {
                drawCircle(MfColors.Rule, r - 1.dp.toPx(), c, style = Stroke(2.dp.toPx()))
            }
        }
        androidx.compose.material3.Text(
            mark,
            fontFamily = DisplayFont,
            fontWeight = FontWeight.Bold,
            fontSize = if (mark.length <= 2) 22.sp else if (mark.length == 3) 18.sp else 15.sp,
            color = if (earned) Color.Black else MfColors.Graphite,
        )
    }
}

/** After saving a session: the badges it earned, quietly. */
@Composable
fun NewBadgesPanel(badges: List<Badge>) {
    if (badges.isEmpty()) return
    Panel {
        Text(if (badges.size == 1) "New badge" else "New badges", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        badges.forEach { b ->
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.semantics(mergeDescendants = true) {}) {
                Medal(b.mark, earned = true, diameter = 44)
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(b.title, style = MaterialTheme.typography.titleMedium)
                    Text(b.detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
