package eu.motionforge.app.feature.lesson

import android.provider.Settings
import androidx.compose.foundation.background
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
import eu.motionforge.app.core.design.CoachStage
import androidx.compose.foundation.layout.fillMaxSize
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
        DemoAvailability.WrittenOnly, DemoAvailability.NotReady -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            // no 3D clip for this lesson: its motion study stands in, so the stage is never empty
            eu.motionforge.app.core.design.MotionStudy(
                coach.studyArt(exercise.id),
                Modifier.fillMaxWidth().height(460.dp),
                description = "Motion study of ${exercise.name}",
            )
            Text(
                if (a == DemoAvailability.WrittenOnly) "This lesson is taught with the picture and written steps."
                else "The 3D demonstration for this lesson isn't ready yet. Follow the picture and the written steps.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp),
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
        CoachStage(exercise.name, accent, Modifier.fillMaxWidth().height(460.dp)) {
            GlbModelView(
                assetPath = manifest.assetPath,
                playback = playback,
                modifier = Modifier.fillMaxSize(),
                allowOrbit = false,
                transparent = true,
                contentDescription = "3D trainer demonstrating ${exercise.name}",
            )
            when (val s = playback.loadState) {
                GlbLoadState.Loading -> Text("Loading the 3D coach…", Modifier.align(Alignment.Center), color = androidx.compose.ui.graphics.Color.White)
                is GlbLoadState.Failed -> {
                    // 3D can't run here: show the motion study on the same stage, with a short note
                    eu.motionforge.app.core.design.MotionStudy(rememberCoach().studyArt(exercise.id), Modifier.fillMaxSize(), description = "Motion study of ${exercise.name}")
                    Text(
                        "3D isn't available on this phone. Showing the motion study.",
                        Modifier.align(Alignment.BottomStart).padding(16.dp),
                        style = MaterialTheme.typography.labelLarge,
                        color = androidx.compose.ui.graphics.Color.White,
                    )
                }
                is GlbLoadState.Loaded -> {
                    val clip = playback.sequence.getOrNull(playback.currentStep)
                    if (clip != null) {
                        val label = DemoSequence.phaseLabel(clip) +
                            if (playback.sequence.size > 1) "  ${playback.currentStep + 1}/${playback.sequence.size}" else ""
                        Text(
                            label,
                            Modifier
                                .align(Alignment.BottomStart)
                                .padding(16.dp)
                                .semantics { liveRegion = LiveRegionMode.Polite },
                            style = MaterialTheme.typography.titleSmall,
                            color = eu.motionforge.app.core.design.onField(accent),
                        )
                    }
                }
            }
        }

        if (playback.loadState is GlbLoadState.Loaded) Column(Modifier.padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                FilledIconButton(
                    onClick = { playback.playing = !playback.playing },
                    modifier = Modifier.size(52.dp),
                    shape = RoundedCornerShape(2.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(containerColor = MaterialTheme.colorScheme.onBackground, contentColor = MaterialTheme.colorScheme.background),
                ) {
                    if (playback.playing) {
                        Text("❚❚", style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { contentDescription = "Pause" })
                    } else {
                        Icon(Icons.Filled.PlayArrow, contentDescription = "Play")
                    }
                }
                OutlinedIconButton(onClick = { playback.replay() }, modifier = Modifier.size(52.dp), shape = RoundedCornerShape(2.dp), border = androidx.compose.foundation.BorderStroke(1.5.dp, MaterialTheme.colorScheme.onBackground)) {
                    Icon(Icons.Filled.Refresh, contentDescription = "Replay")
                }
                SegmentedPill(
                    options = speeds.map { if (it == 1f) "1×" else "$it×" },
                    selectedIndex = speeds.indexOf(playback.speed).coerceAtLeast(0),
                    onSelect = { playback.speed = speeds[it] },
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    compact = true,
                )
            }
            SegmentedPill(
                options = ViewAngle.entries.map { it.label },
                selectedIndex = ViewAngle.entries.indexOf(playback.viewAngle),
                onSelect = { playback.viewAngle = ViewAngle.entries[it] },
                modifier = Modifier.horizontalScroll(rememberScrollState()),
                compact = true,
            )
            if (reduceMotion && !playback.playing) {
                Text(
                    "Animations are reduced on this phone, so the demonstration starts paused.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
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

    Box(modifier.clip(RoundedCornerShape(2.dp)).background(exercise.category.accent)) {
        val failed = playback.loadState is GlbLoadState.Failed
        if (ready != null && !failed) {
            GlbModelView(
                assetPath = ready.manifest.assetPath,
                playback = playback,
                modifier = Modifier.matchParentSize(),
                transparent = true,
                contentDescription = "3D trainer demonstrating ${exercise.name}",
            )
        } else if (availability != DemoAvailability.Checking) {
            // no 3D here: the lesson's motion study shows the movement instead
            eu.motionforge.app.core.design.MotionStudy(coach.studyArt(exercise.id), Modifier.matchParentSize(), description = "Motion study of ${exercise.name}")
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
