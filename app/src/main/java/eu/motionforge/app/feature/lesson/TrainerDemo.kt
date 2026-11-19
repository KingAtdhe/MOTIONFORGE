package eu.motionforge.app.feature.lesson

import android.provider.Settings
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.core.design.ChoiceButton
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.ReviewStatus
import eu.motionforge.app.core.render3d.ClipManifest
import eu.motionforge.app.core.render3d.DemoSequence
import eu.motionforge.app.core.render3d.GlbLoadState
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.render3d.GlbModelView
import eu.motionforge.app.core.render3d.GlbPlayback
import eu.motionforge.app.core.render3d.ViewAngle

private sealed interface DemoAvailability {
    data object Checking : DemoAvailability
    data object WrittenOnly : DemoAvailability
    data object NotReady : DemoAvailability
    data class Ready(val manifest: ClipManifest, val sequence: List<String>) : DemoAvailability
}

/** 3D trainer demonstration for a lesson, with a written fallback whenever 3D is not possible. */
@Composable
fun TrainerDemo(exercise: Exercise) {
    val context = LocalContext.current
    val container = remember { (context.applicationContext as MotionForgeApplication).container }
    val clipsRepo = container.clips
    val coach = rememberCoach()
    val availability by produceState<DemoAvailability>(DemoAvailability.Checking, exercise.id, coach) {
        value = if (exercise.demoAnimation == null) {
            DemoAvailability.WrittenOnly
        } else {
            clipsRepo.trainer(coach).fold(
                onSuccess = { m ->
                    val seq = DemoSequence.resolve(exercise.demoAnimation, m.names)
                    if (seq.isEmpty()) DemoAvailability.NotReady else DemoAvailability.Ready(m, seq)
                },
                onFailure = { DemoAvailability.NotReady },
            )
        }
    }

    when (val a = availability) {
        DemoAvailability.Checking -> Unit
        DemoAvailability.WrittenOnly -> Panel {
            Eyebrow("Demonstration")
            Text("This lesson is taught with written steps only.", style = MaterialTheme.typography.bodyMedium)
        }
        DemoAvailability.NotReady -> Panel {
            Eyebrow("3D demonstration")
            Text(
                "The 3D demonstration for this lesson isn't ready yet. Follow the written steps below.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        is DemoAvailability.Ready -> DemoPlayer(exercise, a.manifest, a.sequence)
    }
}

@Composable
private fun DemoPlayer(exercise: Exercise, manifest: ClipManifest, sequence: List<String>) {
    val context = LocalContext.current
    // Respect the system "remove animations" setting: start paused, user can press Play.
    val reduceMotion = remember {
        Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    }
    val playback = remember(exercise.id) { GlbPlayback(initiallyPlaying = !reduceMotion) }
    LaunchedEffect(playback, sequence) { playback.playSequence(sequence) }
    val speeds = listOf(1f, 0.5f, 0.25f)

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Eyebrow("3D demonstration")
        Box(
            Modifier
                .fillMaxWidth()
                .height(380.dp)
                .clip(RoundedCornerShape(14.dp)),
        ) {
            GlbModelView(
                assetPath = manifest.assetPath,
                playback = playback,
                modifier = Modifier.fillMaxWidth().height(380.dp),
                allowOrbit = false,
                contentDescription = "3D trainer demonstrating ${exercise.name}",
            )
            when (val s = playback.loadState) {
                GlbLoadState.Loading -> Text("Loading trainer…", Modifier.align(Alignment.Center))
                is GlbLoadState.Failed -> Panel(Modifier.align(Alignment.Center).padding(16.dp)) {
                    Eyebrow("3D demonstration unavailable", color = MfColors.Caution)
                    Text(s.reason, style = MaterialTheme.typography.bodyMedium)
                    Text("Follow the written steps below.", style = MaterialTheme.typography.bodyMedium)
                }
                is GlbLoadState.Loaded -> {
                    val clip = playback.sequence.getOrNull(playback.currentStep)
                    if (clip != null) {
                        val label = DemoSequence.phaseLabel(clip) +
                            if (playback.sequence.size > 1) "  ${playback.currentStep + 1}/${playback.sequence.size}" else ""
                        Text(
                            label,
                            style = MaterialTheme.typography.labelLarge,
                            color = MfColors.Chalk,
                            modifier = Modifier
                                .align(Alignment.TopStart)
                                .padding(12.dp)
                                .semantics { liveRegion = LiveRegionMode.Polite },
                        )
                    }
                }
            }
        }

        if (playback.loadState is GlbLoadState.Loaded) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ChoiceButton(if (playback.playing) "Pause" else "Play", selected = false, onClick = { playback.playing = !playback.playing })
                OutlinedButton(onClick = { playback.replay() }) { Text("Replay") }
            }
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                speeds.forEach { sp ->
                    ChoiceButton(if (sp == 1f) "1×" else "$sp×", playback.speed == sp, { playback.speed = sp })
                }
            }
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ViewAngle.entries.forEach { angle ->
                    ChoiceButton(angle.label, playback.viewAngle == angle, { playback.viewAngle = angle })
                }
            }
            if (reduceMotion && !playback.playing) {
                Text(
                    "Animations are reduced on this phone, so the demonstration starts paused.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        val drafts = sequence.mapNotNull { manifest.clip(it) }.any { it.reviewStatus == ReviewStatus.DRAFT_PENDING_COACH_REVIEW }
        if (drafts) {
            Text(
                "Draft demonstration — pending review by a qualified coach. Use it as a visual guide, not as a technique standard.",
                style = MaterialTheme.typography.labelSmall,
                color = MfColors.Caution,
            )
        }
    }
}

/**
 * Controls-free trainer view for the session screen. Falls back to the written steps when the
 * demonstration is unavailable.
 */
@Composable
fun TrainerDemoCompact(exercise: Exercise, playing: Boolean, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val clipsRepo = remember { (context.applicationContext as MotionForgeApplication).container.clips }
    val coach = rememberCoach()
    val availability by produceState<DemoAvailability>(DemoAvailability.Checking, exercise.id, coach) {
        value = clipsRepo.trainer(coach).fold(
            onSuccess = { m ->
                val seq = DemoSequence.resolve(exercise.demoAnimation, m.names)
                if (seq.isEmpty()) DemoAvailability.NotReady else DemoAvailability.Ready(m, seq)
            },
            onFailure = { DemoAvailability.NotReady },
        )
    }
    val ready = availability as? DemoAvailability.Ready
    val playback = remember(exercise.id) { GlbPlayback() }
    LaunchedEffect(playback, ready?.sequence) { ready?.let { playback.playSequence(it.sequence) } }
    LaunchedEffect(playback, playing) { playback.playing = playing }

    Box(modifier.clip(RoundedCornerShape(18.dp))) {
        val failed = playback.loadState is GlbLoadState.Failed
        if (ready != null && !failed) {
            GlbModelView(
                assetPath = ready.manifest.assetPath,
                playback = playback,
                modifier = Modifier.matchParentSize(),
                contentDescription = "3D trainer demonstrating ${exercise.name}",
            )
        } else if (availability != DemoAvailability.Checking) {
            Panel(Modifier.align(Alignment.Center)) {
                Eyebrow("Steps")
                exercise.instructions.forEachIndexed { i, step ->
                    Text("${i + 1}. $step", style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}

/** The coach chosen in Profile (default until preferences load). */
@Composable
private fun rememberCoach(): Coach {
    val context = LocalContext.current
    val prefs = remember { (context.applicationContext as MotionForgeApplication).container.preferences }
    val state by prefs.preferences.collectAsState(initial = null)
    return state?.coach ?: Coach.DEFAULT
}
