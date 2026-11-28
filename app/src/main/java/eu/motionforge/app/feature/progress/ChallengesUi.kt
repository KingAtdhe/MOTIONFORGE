package eu.motionforge.app.feature.progress

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.SecondaryButton
import eu.motionforge.app.core.design.SectionHeader
import eu.motionforge.app.core.design.ThinRule
import eu.motionforge.app.core.design.formatClock
import eu.motionforge.app.core.i18n.Text
import eu.motionforge.app.core.i18n.tr
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.ZoneId

/** "300 of 300 squats", in the challenge's own unit. */
fun challengeAmount(c: Challenge, done: Int): String {
    val d = minOf(done, c.target)
    return when (c.measure) {
        ChallengeMeasure.SESSIONS, ChallengeMeasure.FIGHTING_SESSIONS, ChallengeMeasure.CARDIO_SESSIONS -> "$d of ${c.target} sessions"
        ChallengeMeasure.MINUTES -> "$d of ${c.target} minutes"
        ChallengeMeasure.SQUATS -> "$d of ${c.target} squats"
        ChallengeMeasure.PUSH_UPS -> "$d of ${c.target} push-ups"
        ChallengeMeasure.LUNGES -> "$d of ${c.target} lunges"
        ChallengeMeasure.HOLD_SECONDS -> "${formatClock(d)} of ${formatClock(c.target)} held"
        ChallengeMeasure.EXERCISES -> "$d of ${c.target} exercises"
    }
}

/**
 * Challenges on the You page: the ones joined (running, complete or ended) and a list to join from. Joining, leaving
 * and clearing write straight to the preferences; progress is recomputed from the saved history every time.
 */
@Composable
fun ChallengesSection(history: List<SessionRecord>, joined: List<JoinedChallenge>) {
    val context = LocalContext.current
    val prefs = remember { (context.applicationContext as MotionForgeApplication).container.preferences }
    val scope = rememberCoroutineScope()
    val zone = remember { ZoneId.systemDefault() }
    val today = LocalDate.now(zone)
    val progress = remember(history, joined, today) { Challenges.all(joined, history, today, zone) }
    val running = progress.count { it.status == ChallengeStatus.RUNNING }
    var browsing by rememberSaveable { mutableStateOf(false) }
    var leaving by remember { mutableStateOf<Challenge?>(null) }

    fun save(list: List<JoinedChallenge>) { scope.launch { prefs.setChallenges(list) } }
    fun start(c: Challenge) = save(Challenges.join(joined, c, System.currentTimeMillis(), history, zone))

    SectionHeader(
        "Challenges",
        trailing = if (progress.isEmpty()) null else if (browsing) "Close" else "Find a challenge",
        onTrailing = if (progress.isEmpty()) null else ({ browsing = !browsing }),
    )
    progress.sortedBy { it.status.ordinal }.forEach { p ->
        ChallengeCard(
            p,
            onLeave = { leaving = p.challenge },
            onRestart = { start(p.challenge) },
            onClear = { save(Challenges.remove(joined, p.challenge)) },
            canRestart = running < Challenges.MAX_RUNNING,
        )
    }
    if (progress.isEmpty() || browsing) {
        val open = Challenge.entries.filter { c -> progress.none { it.challenge == c } }
        Column {
            if (progress.isEmpty()) {
                Text(
                    "Optional goals with a time window. Nothing is lost if one ends early; you can start it again.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 6.dp),
                )
            }
            if (running >= Challenges.MAX_RUNNING) {
                Text(
                    "You can run 3 challenges at a time.",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            open.forEachIndexed { i, c ->
                if (i > 0) ThinRule()
                Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                    Medal(c.mark, earned = false, diameter = 44)
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f).semantics(mergeDescendants = true) {}) {
                        Text(c.title, style = MaterialTheme.typography.titleMedium)
                        Text(c.detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    TextButton(
                        onClick = { start(c); browsing = false },
                        enabled = running < Challenges.MAX_RUNNING,
                        modifier = Modifier.semantics { contentDescription = tr("Start ${c.title}") },
                    ) { Text("Start") }
                }
            }
        }
    }

    leaving?.let { c ->
        AlertDialog(
            onDismissRequest = { leaving = null },
            title = { Text("Leave this challenge?") },
            text = { Text("Your sessions stay in your history. You can start it again later, from the beginning.") },
            confirmButton = {
                TextButton(onClick = { save(Challenges.remove(joined, c)); leaving = null }) { Text("Leave") }
            },
            dismissButton = { TextButton(onClick = { leaving = null }) { Text("Cancel") } },
        )
    }
}

@Composable
private fun ChallengeCard(p: ChallengeProgress, onLeave: () -> Unit, onRestart: () -> Unit, onClear: () -> Unit, canRestart: Boolean) {
    val c = p.challenge
    val amount = challengeAmount(c, p.done)
    val state = when (p.status) {
        ChallengeStatus.RUNNING -> "Day ${p.day} of ${c.days}"
        ChallengeStatus.COMPLETE -> "Complete"
        ChallengeStatus.ENDED -> "Ended"
    }
    Panel {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.clearAndSetSemantics { contentDescription = tr(c.title) + ". " + tr(state) + ". " + tr(amount) + "." },
        ) {
            Medal(c.mark, earned = p.status == ChallengeStatus.COMPLETE, diameter = 44)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(c.title, style = MaterialTheme.typography.titleLarge)
                Text(state, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Box(Modifier.fillMaxWidth().height(10.dp).background(MfColors.Rule).clearAndSetSemantics { }) {
            Box(
                Modifier.fillMaxWidth(p.fraction).height(10.dp)
                    .background(if (p.status == ChallengeStatus.COMPLETE) MfColors.Yellow else MfColors.Ink),
            )
        }
        Text(amount, style = MaterialTheme.typography.bodyLarge)
        when (p.status) {
            ChallengeStatus.RUNNING -> Text(c.detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            ChallengeStatus.COMPLETE -> Text("Well done. Clear it, or start it again.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            ChallengeStatus.ENDED -> Text("The window ended. Start it again whenever you like.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            if (p.status == ChallengeStatus.RUNNING) {
                SecondaryButton("Leave", onClick = onLeave, modifier = Modifier.weight(1f))
            } else {
                if (canRestart) SecondaryButton("Start again", onClick = onRestart, modifier = Modifier.weight(1f))
                SecondaryButton("Clear", onClick = onClear, modifier = Modifier.weight(1f))
            }
        }
    }
}

/** After saving a session: the challenges it completed, quietly. */
@Composable
fun CompletedChallengesPanel(done: List<Challenge>) {
    if (done.isEmpty()) return
    Panel {
        Text(if (done.size == 1) "Challenge complete" else "Challenges complete", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        done.forEach { c ->
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.semantics(mergeDescendants = true) {}) {
                Medal(c.mark, earned = true, diameter = 44)
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(c.title, style = MaterialTheme.typography.titleMedium)
                    Text(c.detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
