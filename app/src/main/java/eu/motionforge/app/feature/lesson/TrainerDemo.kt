package eu.motionforge.app.feature.lesson

import android.provider.Settings
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.OutlinedIconButton
import androidx.compose.material3.Surface
import androidx.compose.ui.semantics.contentDescription
import eu.motionforge.app.core.design.SegmentedPill
import eu.motionforge.app.core.design.accent
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
import eu.motionforge.app.core.render3d.defaultViewAngle

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
    val playback = remember(exercise.id) {
        GlbPlayback(initiallyPlaying = !reduceMotion).apply { viewAngle = defaultViewAngle(exercise.recommendedView.wireName) }
    }
    LaunchedEffect(playback, sequence) { playback.playSequence(sequence) }
    val speeds = listOf(1f, 0.5f, 0.25f)

    val accent = exercise.category.accent
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(420.dp)
                .clip(RoundedCornerShape(24.dp))
                .border(1.dp, accent.copy(alpha = 0.45f), RoundedCornerShape(24.dp)),
        ) {
            GlbModelView(
                assetPath = manifest.assetPath,
                playback = playback,
                modifier = Modifier.fillMaxWidth().height(420.dp),
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
                        Surface(
                            modifier = Modifier
                                .align(Alignment.TopStart)
                                .padding(12.dp)
                                .semantics { liveRegion = LiveRegionMode.Polite },
                            shape = RoundedCornerShape(50),
                            color = MfColors.Ink.copy(alpha = 0.78f),
                        ) {
                            Text(
                                label.uppercase(),
                                Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = accent,
                            )
                        }
                    }
                }
            }
        }

        if (playback.loadState is GlbLoadState.Loaded) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                FilledIconButton(
                    onClick = { playback.playing = !playback.playing },
                    modifier = Modifier.size(52.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(containerColor = accent, contentColor = MfColors.Ink),
                ) {
                    if (playback.playing) {
                        Text("❚❚", style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { contentDescription = "Pause" })
                    } else {
                        Icon(Icons.Filled.PlayArrow, contentDescription = "Play")
                    }
                }
                OutlinedIconButton(onClick = { playback.replay() }, modifier = Modifier.size(52.dp)) {
                    Icon(Icons.Filled.Refresh, contentDescription = "Replay")
                }
                SegmentedPill(
                    options = speeds.map { if (it == 1f) "1×" else "$it×" },
                    selectedIndex = speeds.indexOf(playback.speed).coerceAtLeast(0),
                    onSelect = { playback.speed = speeds[it] },
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    accent = MfColors.Chalk,
                )
            }
            SegmentedPill(
                options = ViewAngle.entries.map { it.label },
                selectedIndex = ViewAngle.entries.indexOf(playback.viewAngle),
                onSelect = { playback.viewAngle = ViewAngle.entries[it] },
                modifier = Modifier.horizontalScroll(rememberScrollState()),
                accent = accent,
            )
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
    val playback = remember(exercise.id) { GlbPlayback().apply { viewAngle = defaultViewAngle(exercise.recommendedView.wireName) } }
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
