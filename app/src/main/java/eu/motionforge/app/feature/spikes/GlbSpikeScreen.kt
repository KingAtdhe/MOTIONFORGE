package eu.motionforge.app.feature.spikes

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenHeader
import eu.motionforge.app.core.render3d.GlbLoadState
import eu.motionforge.app.core.render3d.GlbModelView
import eu.motionforge.app.core.render3d.GlbPlayback
import eu.motionforge.app.core.render3d.ViewAngle

/**
 * Developer screen: loads the trainer GLB and lets you play every clip with orbit, pause,
 * replay, slow motion and view angles. Used to check new Blender exports on real devices.
 */
@Composable
fun GlbSpikeScreen(onBack: () -> Unit) {
    val playback = remember { GlbPlayback() }
    val speeds = listOf(1f, 0.5f, 0.25f)

    Column(Modifier.fillMaxSize()) {
        Box(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) { ScreenHeader("3D animation", onBack) }

        Box(Modifier.fillMaxWidth().weight(1f)) {
            GlbModelView(
                assetPath = SPIKE_ASSET,
                playback = playback,
                modifier = Modifier.fillMaxSize(),
                allowOrbit = true,
                contentDescription = "3D trainer clip preview",
            )
            when (val s = playback.loadState) {
                GlbLoadState.Loading -> Text("Loading 3D model…", Modifier.align(Alignment.Center))
                is GlbLoadState.Failed -> StaticFallback(s.reason, Modifier.align(Alignment.Center).padding(20.dp))
                is GlbLoadState.Loaded -> Unit
            }
        }

        val loaded = playback.loadState as? GlbLoadState.Loaded
        if (loaded != null) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Eyebrow("Clip")
                if (loaded.clips.isEmpty()) {
                    Text("This model has no animation clips.", color = MfColors.Caution)
                } else {
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        loaded.clips.forEach { clip ->
                            val selected = playback.sequence == listOf(clip.name)
                            if (selected) {
                                Button(onClick = { playback.playSequence(listOf(clip.name)) }) { Text(clip.name) }
                            } else {
                                OutlinedButton(onClick = { playback.playSequence(listOf(clip.name)) }) { Text(clip.name) }
                            }
                        }
                    }
                    LaunchedEffect(loaded) {
                        if (playback.sequence.isEmpty()) playback.playSequence(listOf(loaded.clips.first().name))
                    }
                    val current = loaded.clips.firstOrNull { listOf(it.name) == playback.sequence }
                    if (current != null) {
                        Text(
                            "${current.name} · ${"%.2f".format(current.durationSeconds)} s · drag to orbit",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { playback.playing = !playback.playing }) {
                            Text(if (playback.playing) "Pause" else "Play")
                        }
                        OutlinedButton(onClick = { playback.replay() }) { Text("Replay") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ViewAngle.entries.forEach { a ->
                            if (playback.viewAngle == a) {
                                Button(onClick = { playback.viewAngle = a }) { Text(a.label) }
                            } else {
                                OutlinedButton(onClick = { playback.viewAngle = a }) { Text(a.label) }
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        speeds.forEach { speed ->
                            val label = if (speed == 1f) "1×" else "$speed×"
                            if (playback.speed == speed) {
                                Button(onClick = { playback.speed = speed }) { Text(label) }
                            } else {
                                OutlinedButton(onClick = { playback.speed = speed }) { Text(label) }
                            }
                        }
                    }
                }
            }
        }
    }
}

/** Text-only fallback shown when 3D rendering fails. */
@Composable
private fun StaticFallback(reason: String, modifier: Modifier = Modifier) {
    Panel(modifier) {
        Eyebrow("3D demo unavailable", color = MfColors.Caution)
        Text(reason, style = MaterialTheme.typography.bodyMedium)
        Text(
            "Lessons will show written step-by-step instructions instead of the 3D demonstration.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private const val SPIKE_ASSET = "models/coach_f.glb"
