package eu.motionforge.app.feature.session

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import eu.motionforge.app.core.camera.PoseCameraPane
import eu.motionforge.app.core.design.ChoiceButton
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.PrimaryButton
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.design.StatTile
import eu.motionforge.app.core.design.TrackingStatusChip
import eu.motionforge.app.core.design.accent
import eu.motionforge.app.core.design.formatClock
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.core.movement.FormFeedback
import eu.motionforge.app.core.pose.TrackingState
import eu.motionforge.app.feature.lesson.TrainerDemoCompact

@Composable
fun SessionScreen(
    viewModel: SessionViewModel,
    exercisesById: Map<String, Exercise>,
    onClose: () -> Unit,
    onOpenProgress: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val tracking by viewModel.tracking.collectAsStateWithLifecycle()
    val form by viewModel.form.collectAsStateWithLifecycle()
    val save by viewModel.save.collectAsStateWithLifecycle()

    // Keep the screen awake while a session is in progress.
    val view = LocalView.current
    val active = state.phase == SessionPhase.RUNNING || state.phase == SessionPhase.PAUSED
    DisposableEffect(view, active) {
        view.keepScreenOn = active
        onDispose { view.keepScreenOn = false }
    }

    when (state.phase) {
        SessionPhase.READY -> SetupStage(state.plan, onStart = { camera -> viewModel.onEvent(SessionEvent.Start(camera)) }, onClose = onClose)
        SessionPhase.RUNNING, SessionPhase.PAUSED -> {
            BackHandler { viewModel.onEvent(SessionEvent.Stop) }
            RunningStage(state, tracking, form, exercisesById, viewModel)
        }
        SessionPhase.FINISHED -> SummaryStage(state, save, onSave = viewModel::saveSession, onClose = onClose, onOpenProgress = onOpenProgress)
    }
}

// ----------------------------------------------------------------------------- setup
@Composable
private fun SetupStage(plan: SessionPlan, onStart: (camera: Boolean) -> Unit, onClose: () -> Unit) {
    val context = LocalContext.current
    var denied by rememberSaveable { mutableStateOf(false) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) onStart(true) else denied = true
    }
    val hasRepCounting = plan.steps.any { it is SessionStep.Work && it.countsReps }

    ScreenColumn(title = plan.title, onBack = onClose) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile(formatClock(plan.totalSeconds), "Total time", Modifier.weight(1f), accent = plan.type.accent)
            StatTile("${plan.workCount}", if (plan.workCount == 1) "Exercise" else "Exercises", Modifier.weight(1f))
        }
        Panel {
            Eyebrow("Plan")
            plan.steps.forEach { step ->
                when (step) {
                    is SessionStep.Work -> Text("${step.name} · ${step.durationSeconds} s", style = MaterialTheme.typography.bodyLarge)
                    is SessionStep.Rest -> Text("Rest · ${step.durationSeconds} s", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        Panel {
            Eyebrow("Before you start", color = MfColors.Caution)
            Text(
                "Clear the floor around you and go at your own pace. Stop if you feel pain, dizziness or unusual discomfort. " +
                    "Fighting fundamentals are non-contact: never strike people or objects.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Panel {
            Eyebrow("Camera (optional)")
            Text(
                "With the camera on, you see yourself with a tracking skeleton" +
                    (if (hasRepCounting) " and squats are counted automatically (experimental)." else ".") +
                    " Images are processed on this phone, kept in memory only and never saved or uploaded. " +
                    "Prop the phone up 2–3 m away so your whole body is in view.",
                style = MaterialTheme.typography.bodyMedium,
            )
            if (denied) {
                Text("Camera access was denied. You can still train without it.", style = MaterialTheme.typography.bodyMedium, color = MfColors.Caution)
            }
        }
        PrimaryButton("Start with camera", onClick = {
            val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
            if (granted) onStart(true) else launcher.launch(Manifest.permission.CAMERA)
        })
        OutlinedButton(onClick = { onStart(false) }, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
            Text("Start without camera")
        }
    }
}

// ----------------------------------------------------------------------------- running
@Composable
private fun RunningStage(
    state: SessionState,
    tracking: TrackingState,
    form: FormFeedback?,
    exercisesById: Map<String, Exercise>,
    viewModel: SessionViewModel,
) {
    val step = state.currentStep
    val paused = state.phase == SessionPhase.PAUSED
    var showDemo by rememberSaveable { mutableStateOf(false) }
    var lensFacing by rememberSaveable { mutableIntStateOf(CameraSelector.LENS_FACING_FRONT) }
    val accent = state.plan.type.accent
    val cameraVisible = state.cameraUsed && !showDemo && step is SessionStep.Work
    LaunchedEffect(cameraVisible) { if (!cameraVisible) viewModel.onCameraHidden() }

    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        LinearProgressIndicator(
            progress = { (state.elapsedTotal.toFloat() / state.plan.totalSeconds).coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth(),
            color = accent,
        )
        when (step) {
            is SessionStep.Work -> {
                Eyebrow("Exercise ${state.workIndex} of ${state.plan.workCount}", color = accent)
                Text(step.name.uppercase(), style = MaterialTheme.typography.headlineLarge, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            }
            is SessionStep.Rest -> {
                Eyebrow("Rest", color = MfColors.Muted)
                Text("NEXT: ${step.nextName.uppercase()}", style = MaterialTheme.typography.headlineLarge, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            }
        }

        Box(Modifier.fillMaxWidth().weight(1f).clip(RoundedCornerShape(18.dp))) {
            val exercise = (step as? SessionStep.Work)?.let { exercisesById[it.exerciseId] }
                ?: (step as? SessionStep.Rest)?.let { rest -> exercisesById.values.firstOrNull { it.name == rest.nextName } }
            when {
                cameraVisible -> {
                    PoseCameraPane(lensFacing = lensFacing, showOverlay = true, onOutput = viewModel::onPose, modifier = Modifier.fillMaxSize())
                    TrackingStatusChip(tracking, Modifier.align(Alignment.TopCenter).padding(top = 10.dp))
                    val drill = (step as? SessionStep.Work)?.formDrill
                    if (form != null && drill != null) {
                        FormCueCard(form, drill, Modifier.align(Alignment.BottomCenter).padding(12.dp))
                    }
                }
                exercise != null -> TrainerDemoCompact(exercise, playing = !paused, modifier = Modifier.fillMaxSize())
            }
        }

        Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(
                formatClock(state.remainingInStep),
                style = MaterialTheme.typography.displayLarge,
                color = if (paused) MfColors.Muted else MfColors.Chalk,
            )
            Column(Modifier.padding(bottom = 14.dp)) {
                if (paused) Eyebrow("Paused", color = MfColors.Caution)
                if (step is SessionStep.Work && step.countsReps && state.cameraUsed) {
                    Text("${state.stepReps}", style = MaterialTheme.typography.displaySmall, color = accent)
                    Eyebrow(if (tracking.allowsFeedback && !showDemo) "Reps (experimental)" else "Reps — counting paused")
                }
            }
        }

        val cue: String? = when (step) {
            is SessionStep.Rest -> "Breathe and shake out. Skip the rest when you're ready."
            is SessionStep.Work -> {
                val cues = exercisesById[step.exerciseId]?.commonCues.orEmpty()
                when {
                    step.countsReps && cameraVisible && !tracking.allowsFeedback -> "Counting is paused until tracking is steady."
                    cameraVisible && !step.countsReps -> "The camera does not assess this movement — use it as a mirror."
                    cues.isNotEmpty() -> cues[(state.stepElapsed / 8) % cues.size]
                    else -> null
                }
            }
        }
        if (cue != null) Text(cue, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)

        if (state.cameraUsed && step is SessionStep.Work) {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ChoiceButton("Camera", !showDemo, { showDemo = false })
                ChoiceButton("Trainer demo", showDemo, { showDemo = true })
                if (!showDemo) {
                    OutlinedButton(onClick = {
                        lensFacing = if (lensFacing == CameraSelector.LENS_FACING_FRONT) CameraSelector.LENS_FACING_BACK else CameraSelector.LENS_FACING_FRONT
                    }) { Text("Flip camera") }
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PrimaryButton(
                if (paused) "Resume" else "Pause",
                onClick = { viewModel.onEvent(if (paused) SessionEvent.Resume else SessionEvent.Pause) },
                modifier = Modifier.weight(1.4f),
            )
            OutlinedButton(onClick = { viewModel.onEvent(SessionEvent.Skip) }, modifier = Modifier.weight(1f).heightIn(min = 56.dp)) { Text("Skip") }
            OutlinedButton(onClick = { viewModel.onEvent(SessionEvent.Stop) }, modifier = Modifier.weight(1f).heightIn(min = 56.dp)) { Text("End", color = MfColors.Halt) }
        }
    }
}

// ----------------------------------------------------------------------------- summary
@Composable
private fun SummaryStage(
    state: SessionState,
    save: SaveState,
    onSave: (Int?) -> Unit,
    onClose: () -> Unit,
    onOpenProgress: () -> Unit,
) {
    var effort by rememberSaveable { mutableIntStateOf(0) }
    val reps = state.results.mapNotNull { it.repetitions }
    BackHandler(onBack = onClose)

    ScreenColumn(title = if (state.endedEarly) "Session ended" else "Session complete") {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile(formatClock(state.workSeconds), "Active time", Modifier.weight(1f), accent = state.plan.type.accent)
            StatTile("${state.results.size}", "Exercises", Modifier.weight(1f))
            if (reps.isNotEmpty()) StatTile("${reps.sum()}", "Reps", Modifier.weight(1f))
        }
        if (state.results.isNotEmpty()) {
            Panel {
                Eyebrow("What you did")
                state.results.forEach { r ->
                    val repText = r.repetitions?.let { " · $it reps (experimental count)" }.orEmpty()
                    Text("${r.name} · ${formatClock(r.elapsedSeconds)}$repText", style = MaterialTheme.typography.bodyLarge)
                    if (r.trackingQuality == TrackingQuality.UNAVAILABLE) {
                        Text("Tracking was mostly unavailable, so nothing was counted.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        when {
            !state.isSaveable -> {
                Panel { Text("This session was too short to save.", style = MaterialTheme.typography.bodyLarge) }
                PrimaryButton("Done", onClick = onClose)
            }
            save == SaveState.SAVED -> {
                Panel { Text("Saved to your progress on this phone.", style = MaterialTheme.typography.bodyLarge) }
                PrimaryButton("See progress", onClick = onOpenProgress)
                TextButton(onClick = onClose, modifier = Modifier.fillMaxWidth()) { Text("Done") }
            }
            else -> {
                Eyebrow("How hard did it feel? (optional)")
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    (1..10).forEach { n -> ChoiceButton("$n", effort == n, { effort = if (effort == n) 0 else n }) }
                }
                Text("1 = very easy · 10 = maximum effort", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (save == SaveState.FAILED) Text("Saving failed. Please try again.", color = MfColors.Halt)
                PrimaryButton(if (save == SaveState.SAVING) "Saving…" else "Save session", onClick = { onSave(effort.takeIf { it in 1..10 }) }, enabled = save != SaveState.SAVING)
                TextButton(onClick = onClose, modifier = Modifier.fillMaxWidth()) { Text("Discard") }
            }
        }
    }
}

/** Boxing form cue overlay. Always labelled experimental; never certifies technique. */
@Composable
private fun FormCueCard(form: FormFeedback, drill: BoxingDrill, modifier: Modifier = Modifier) {
    val (color, text) = when (form) {
        is FormFeedback.NotAssessing -> MfColors.Muted to "Form check paused — keep your whole body, hands and feet in view."
        is FormFeedback.Steady -> MfColors.Signal to "No adjustment cues right now."
        is FormFeedback.Cue -> MfColors.Caution to form.issue.message
    }
    androidx.compose.material3.Surface(
        modifier = modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite },
        shape = RoundedCornerShape(14.dp),
        color = MfColors.Ink.copy(alpha = 0.85f),
        border = androidx.compose.foundation.BorderStroke(1.dp, color),
    ) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Eyebrow(if (drill == BoxingDrill.JAB) "Form check (experimental) · jabs ${form.jabs}" else "Form check (experimental)", color = color)
            Text(text, style = MaterialTheme.typography.bodyMedium, color = MfColors.Chalk)
        }
    }
}
