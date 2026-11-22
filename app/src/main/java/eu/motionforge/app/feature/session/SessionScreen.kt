package eu.motionforge.app.feature.session

import androidx.compose.ui.text.drawText
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import eu.motionforge.app.core.camera.PoseCameraPane
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MeasureScale
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.MfType
import eu.motionforge.app.core.design.MotionForgeTheme
import eu.motionforge.app.core.design.MotionStudy
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.PlateShape
import eu.motionforge.app.core.design.PrimaryButton
import eu.motionforge.app.core.design.RoundAction
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.design.SecondaryButton
import eu.motionforge.app.core.design.SegmentedPill
import eu.motionforge.app.core.design.StatTile
import eu.motionforge.app.core.design.TrackingStatusChip
import eu.motionforge.app.core.design.formatClock
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.pose.TrackingState
import eu.motionforge.app.feature.lesson.TrainerDemoCompact

@Composable
fun SessionScreen(
    viewModel: SessionViewModel,
    exercisesById: Map<String, Exercise>,
    coach: Coach,
    voiceCues: Boolean,
    onVoiceCuesChange: (Boolean) -> Unit,
    onClose: () -> Unit,
    onOpenProgress: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val tracking by viewModel.tracking.collectAsStateWithLifecycle()
    val coaching by viewModel.coaching.collectAsStateWithLifecycle()
    val save by viewModel.save.collectAsStateWithLifecycle()

    // Voice coach: the phone's text-to-speech, alive while this screen is.
    val appContext = LocalContext.current.applicationContext
    val speaker = remember { eu.motionforge.app.core.coaching.CoachSpeaker(appContext) }
    DisposableEffect(speaker) { onDispose { speaker.shutdown() } }
    val voiceOn by rememberUpdatedState(voiceCues)
    LaunchedEffect(voiceCues) { if (!voiceCues) speaker.stop() }
    LaunchedEffect(viewModel) { viewModel.speech.collect { if (voiceOn) speaker.speak(it) } }

    // Keep the screen awake while a session is in progress.
    val view = LocalView.current
    val active = state.phase == SessionPhase.RUNNING || state.phase == SessionPhase.PAUSED
    DisposableEffect(view, active) {
        view.keepScreenOn = active
        onDispose { view.keepScreenOn = false }
    }

    // Outside the app: the ongoing notification / Live Update, and headphone buttons.
    val notifier = remember { WorkoutNotifier(appContext) }
    LaunchedEffect(state.stepIndex, state.phase, state.stepReps, state.remainingInStep / 15) {
        if (active) notifier.update(state) else notifier.clear()
    }
    DisposableEffect(notifier) { onDispose { notifier.clear() } }
    val currentState by rememberUpdatedState(state)
    val buttons = remember(active) {
        if (!active) null else WorkoutButtons(
            appContext,
            onToggle = { viewModel.onEvent(if (currentState.phase == SessionPhase.PAUSED) SessionEvent.Resume else SessionEvent.Pause) },
            onNext = { viewModel.onEvent(SessionEvent.Skip) },
        )
    }
    DisposableEffect(buttons) { onDispose { buttons?.release() } }
    LaunchedEffect(buttons, state.phase) { buttons?.setPlaying(state.phase == SessionPhase.RUNNING) }

    when (state.phase) {
        SessionPhase.READY -> SetupStage(state.plan, coach, onStart = { camera -> viewModel.onEvent(SessionEvent.Start(camera)) }, onClose = onClose)
        SessionPhase.RUNNING, SessionPhase.PAUSED -> {
            BackHandler { viewModel.onEvent(SessionEvent.Stop) }
            // the workout runs on the black plate: camera and coach stand out, light status icons
            val window = androidx.activity.compose.LocalActivity.current?.window
            DisposableEffect(window) {
                val ctl = window?.let { androidx.core.view.WindowCompat.getInsetsController(it, it.decorView) }
                ctl?.isAppearanceLightStatusBars = false
                ctl?.isAppearanceLightNavigationBars = false
                onDispose {
                    ctl?.isAppearanceLightStatusBars = true
                    ctl?.isAppearanceLightNavigationBars = true
                }
            }
            MotionForgeTheme(night = true) {
                Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
                    RunningStage(state, tracking, coaching, exercisesById, coach, viewModel, voiceCues, onVoiceCuesChange)
                }
            }
        }
        SessionPhase.FINISHED -> SummaryStage(
            state, save, coach, remember(state.phase) { viewModel.plateFrames() }, exercisesById,
            onSave = viewModel::saveSession,
            onClose = { viewModel.onClosed(); onClose() },
            onOpenProgress = { viewModel.onClosed(); onOpenProgress() },
        )
    }
}

// ----------------------------------------------------------------------------- phone setup

/** Before the first move: where to put the phone, what the camera does, then start — all in thumb reach. */
@Composable
private fun SetupStage(plan: SessionPlan, coach: Coach, onStart: (camera: Boolean) -> Unit, onClose: () -> Unit) {
    val context = LocalContext.current
    var denied by rememberSaveable { mutableStateOf(false) }
    var wantsCamera by rememberSaveable { mutableStateOf(true) }
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) onStart(true) else denied = true
    }
    fun startCameraOrNot() {
        if (!wantsCamera) { onStart(false); return }
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        if (granted) onStart(true) else cameraLauncher.launch(Manifest.permission.CAMERA)
    }
    // the workout notification is asked for first, once; whatever the answer, the session goes on
    val notifyLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { startCameraOrNot() }
    fun begin(camera: Boolean) {
        wantsCamera = camera
        val needsNotify = Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        if (needsNotify) notifyLauncher.launch(Manifest.permission.POST_NOTIFICATIONS) else startCameraOrNot()
    }
    val hasRepCounting = plan.steps.any { it is SessionStep.Work && it.countsReps }
    val work = plan.steps.filterIsInstance<SessionStep.Work>()

    Box(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().padding(bottom = 156.dp)) {
            ScreenColumn(title = plan.title, onBack = onClose) {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(formatClock(plan.totalSeconds), style = MfType.Numeral)
                    Text("  ${work.size} move${if (work.size == 1) "" else "s"}", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 8.dp))
                }
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    work.forEachIndexed { i, step ->
                        Column(Modifier.width(88.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            MotionStudy(coach.studyArt(step.exerciseId), Modifier.fillMaxWidth().height(110.dp), crop = true)
                            Text("${i + 1}  ${step.name}", style = MaterialTheme.typography.labelSmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
                eu.motionforge.app.core.design.SectionHeader("Set up the phone")
                PlacementDiagram(Modifier.fillMaxWidth().height(170.dp))
                Text(
                    "Prop the phone at hip height, about 2 m away, turned so it sees you from a front corner. " +
                        "Your whole body, head to feet, should fit in the picture.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "With the camera on you see yourself with a tracking trace" +
                        (if (hasRepCounting) ", and squats are counted (experimental)." else ".") +
                        " Images are processed on this phone, kept in memory only and never saved or uploaded.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (denied) {
                    Text("Camera access was denied. You can still train without it.", style = MaterialTheme.typography.bodyMedium, color = MfColors.Halt)
                }
                Panel {
                    Eyebrow("Before you start")
                    Text(
                        "Clear the floor around you and go at your own pace. Stop if you feel pain, dizziness or unusual discomfort. " +
                            "Fighting fundamentals are non-contact: never strike people or objects.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
        Column(
            Modifier.align(Alignment.BottomCenter).fillMaxWidth().background(MaterialTheme.colorScheme.background).padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            PrimaryButton("Start with camera", onClick = { begin(true) }, trailing = formatClock(plan.totalSeconds))
            SecondaryButton("Start without camera", onClick = { begin(false) })
        }
    }
}

/** Side view: the phone on a low stand, about 2 m from where you stand, sightline dashed. */
@Composable
private fun PlacementDiagram(modifier: Modifier = Modifier) {
    val ink = MaterialTheme.colorScheme.onBackground
    val muted = MaterialTheme.colorScheme.onSurfaceVariant
    val label = MaterialTheme.typography.labelMedium
    val measurer = androidx.compose.ui.text.rememberTextMeasurer()
    Canvas(modifier.semantics { contentDescription = "The phone stands at hip height about 2 metres in front of you, tilted to see your whole body" }) {
        val floor = size.height - 18f
        drawLine(muted, Offset(0f, floor), Offset(size.width, floor), 2f)
        // phone on a stand
        val px = size.width * 0.14f
        val ph = size.height * 0.46f
        drawLine(ink, Offset(px, floor), Offset(px, floor - ph), 4f)
        drawRect(MfColors.Yellow, topLeft = Offset(px - 8f, floor - ph - 46f), size = androidx.compose.ui.geometry.Size(16f, 46f))
        // person
        val bx = size.width * 0.82f
        val head = floor - size.height * 0.78f
        drawCircle(ink, 13f, Offset(bx, head))
        drawLine(ink, Offset(bx, head + 14f), Offset(bx, floor - size.height * 0.38f), 6f, cap = StrokeCap.Round)
        drawLine(ink, Offset(bx, floor - size.height * 0.38f), Offset(bx - 18f, floor), 6f, cap = StrokeCap.Round)
        drawLine(ink, Offset(bx, floor - size.height * 0.38f), Offset(bx + 18f, floor), 6f, cap = StrokeCap.Round)
        drawLine(ink, Offset(bx, head + 34f), Offset(bx - 26f, head + 70f), 6f, cap = StrokeCap.Round)
        drawLine(ink, Offset(bx, head + 34f), Offset(bx + 26f, head + 70f), 6f, cap = StrokeCap.Round)
        // view cone and distance
        val eye = Offset(px, floor - ph - 23f)
        val dash = PathEffect.dashPathEffect(floatArrayOf(10f, 8f))
        drawLine(muted, eye, Offset(bx - 30f, head - 20f), 2f, pathEffect = dash)
        drawLine(muted, eye, Offset(bx - 30f, floor), 2f, pathEffect = dash)
        drawLine(ink, Offset(px, floor + 8f), Offset(bx, floor + 8f), 2f)
        val t = measurer.measure("about 2 m", label)
        drawText(t, color = ink, topLeft = Offset((px + bx) / 2 - t.size.width / 2, floor - t.size.height - 6f))
    }
}

// ----------------------------------------------------------------------------- running

/**
 * The workout, read from the floor 2 m away: the move's name, then the live number at 120 sp in timing yellow, the
 * timer running along the measuring scale, the camera mirror with your body trace. Tap anywhere to pause; controls
 * only appear while paused.
 */
@Composable
private fun RunningStage(
    state: SessionState,
    tracking: TrackingState,
    coaching: LiveCoaching?,
    exercisesById: Map<String, Exercise>,
    coach: Coach,
    viewModel: SessionViewModel,
    voiceCues: Boolean,
    onVoiceCuesChange: (Boolean) -> Unit,
) {
    val step = state.currentStep
    val paused = state.phase == SessionPhase.PAUSED
    var showDemo by rememberSaveable { mutableStateOf(false) }
    var lensFacing by rememberSaveable { mutableIntStateOf(CameraSelector.LENS_FACING_FRONT) }
    val cameraVisible = state.cameraUsed && !showDemo && step is SessionStep.Work
    LaunchedEffect(cameraVisible) { if (!cameraVisible) viewModel.onCameraHidden() }
    val context = LocalContext.current
    val reduceMotion = remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }

    // a counted rep: a short tick under the finger and the number briefly swelling, like an exposure landing
    val haptics = LocalHapticFeedback.current
    val pulse = remember { Animatable(1f) }
    LaunchedEffect(state.stepReps) {
        if (state.stepReps > 0) {
            haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
            if (!reduceMotion) { pulse.snapTo(1.14f); pulse.animateTo(1f, tween(260)) }
        }
    }
    // a new move: the shutter closes and opens (a plain fade with reduced motion)
    val shutter = remember { Animatable(0f) }
    LaunchedEffect(state.stepIndex) {
        shutter.snapTo(1f); shutter.animateTo(0f, tween(if (reduceMotion) 150 else 380))
    }

    Box(
        Modifier
            .fillMaxSize()
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                enabled = !paused,
                onClickLabel = "Pause",
            ) { viewModel.onEvent(SessionEvent.Pause) },
    ) {
        Column(Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            var showRestored by rememberSaveable { mutableStateOf(viewModel.wasRestored) }
            LaunchedEffect(paused) { if (!paused) showRestored = false }
            if (showRestored && paused) {
                Surface(shape = PlateShape, color = MaterialTheme.colorScheme.surface, modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite }) {
                    Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                        Eyebrow("Picked up where you left off", color = MfColors.Yellow)
                        Text(
                            "The app was closed during your workout. Everything you'd done is kept; time while it was closed isn't counted. Press Resume when you're ready.",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                }
            }
            Text(
                when (step) {
                    is SessionStep.Work -> "Exercise ${state.workIndex} of ${state.plan.workCount}"
                    is SessionStep.Rest -> "Rest"
                },
                style = MaterialTheme.typography.titleMedium,
                color = MfColors.OnNightMuted,
            )
            Text(
                when (step) {
                    is SessionStep.Work -> step.name
                    is SessionStep.Rest -> "Next: ${step.nextName}"
                },
                style = MaterialTheme.typography.headlineLarge.copy(fontSize = 32.sp, lineHeight = 35.sp),
                maxLines = 2,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )

            // the live number: reps when they're counted, otherwise the time left
            val countsReps = step is SessionStep.Work && step.countsReps && state.cameraUsed
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    if (countsReps) "${state.stepReps}" else formatClock(state.remainingInStep),
                    style = MfType.NumeralHuge,
                    color = if (paused) MfColors.OnNightMuted else MfColors.Yellow,
                    modifier = Modifier.scale(pulse.value).semantics {
                        contentDescription = if (countsReps) "${state.stepReps} reps" else "${state.remainingInStep} seconds left"
                    },
                )
                Spacer(Modifier.width(12.dp))
                Column(Modifier.padding(bottom = 16.dp)) {
                    if (countsReps) {
                        Text("reps", style = MaterialTheme.typography.headlineSmall)
                        Text(formatClock(state.remainingInStep) + " left", style = MfType.NumeralSmall, color = MfColors.OnNightMuted)
                    } else {
                        Text(if (paused) "paused" else if (step is SessionStep.Rest) "rest" else "left", style = MaterialTheme.typography.headlineSmall)
                    }
                }
            }
            MeasureScale(
                color = MfColors.OnNightMuted,
                fraction = 1f - state.remainingInStep.toFloat() / step.durationSeconds.coerceAtLeast(1),
                fill = if (step is SessionStep.Rest) MfColors.SignalOnNight else MfColors.Yellow,
            )

            Box(Modifier.fillMaxWidth().weight(1f).clip(PlateShape).background(MfColors.NightRaised)) {
                val exercise = (step as? SessionStep.Work)?.let { exercisesById[it.exerciseId] }
                    ?: (step as? SessionStep.Rest)?.let { rest -> exercisesById.values.firstOrNull { it.name == rest.nextName } }
                when {
                    cameraVisible -> {
                        PoseCameraPane(lensFacing = lensFacing, showOverlay = true, onOutput = viewModel::onPose, modifier = Modifier.fillMaxSize())
                        TrackingStatusChip(tracking, Modifier.align(Alignment.TopStart).padding(10.dp))
                        if (exercise != null) {
                            // the coach's motion study as a small inset: the movement to match
                            MotionStudy(coach.studyArt(exercise.id), Modifier.align(Alignment.TopEnd).padding(10.dp).width(78.dp).height(98.dp))
                        }
                        if (coaching != null) CoachingCard(coaching, Modifier.align(Alignment.BottomCenter).padding(10.dp))
                    }
                    exercise != null -> TrainerDemoCompact(exercise, playing = !paused, modifier = Modifier.fillMaxSize())
                }
            }

            val cue: String? = when (step) {
                is SessionStep.Rest -> "Breathe and shake out."
                is SessionStep.Work -> {
                    val cues = exercisesById[step.exerciseId]?.commonCues.orEmpty()
                    when {
                        step.countsReps && cameraVisible && !tracking.allowsFeedback -> "Counting is paused until tracking is steady."
                        cameraVisible && !step.countsReps && step.formDrill == null -> "The camera doesn't assess this move. Use it as a mirror."
                        cues.isNotEmpty() -> cues[(state.stepElapsed / 8) % cues.size]
                        else -> null
                    }
                }
            }
            if (cue != null) Text(cue, style = MaterialTheme.typography.titleMedium, color = MfColors.OnNightMuted)

            if (paused) {
                PausedControls(state, step, showDemo, onDemo = { showDemo = it }, lensFacing, onFlip = {
                    lensFacing = if (lensFacing == CameraSelector.LENS_FACING_FRONT) CameraSelector.LENS_FACING_BACK else CameraSelector.LENS_FACING_FRONT
                }, voiceCues, onVoiceCuesChange, viewModel)
            } else {
                Text(
                    if (step is SessionStep.Rest) "Tap anywhere to pause. Skip the rest from the pause screen." else "Tap anywhere to pause",
                    style = MaterialTheme.typography.labelLarge,
                    color = MfColors.OnNightMuted,
                    modifier = Modifier.align(Alignment.CenterHorizontally).padding(vertical = 10.dp),
                )
            }
        }
        // shutter blades on a step change
        if (shutter.value > 0.001f) {
            Canvas(Modifier.fillMaxSize()) {
                val h = size.height / 2f * shutter.value
                if (reduceMotion) drawRect(Color.Black.copy(alpha = shutter.value))
                else {
                    drawRect(Color.Black, size = androidx.compose.ui.geometry.Size(size.width, h))
                    drawRect(Color.Black, topLeft = Offset(0f, size.height - h), size = androidx.compose.ui.geometry.Size(size.width, h))
                }
            }
        }
    }
}

@Composable
private fun PausedControls(
    state: SessionState,
    step: SessionStep,
    showDemo: Boolean,
    onDemo: (Boolean) -> Unit,
    lensFacing: Int,
    onFlip: () -> Unit,
    voiceCues: Boolean,
    onVoiceCuesChange: (Boolean) -> Unit,
    viewModel: SessionViewModel,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
            if (state.cameraUsed && step is SessionStep.Work) {
                SegmentedPill(options = listOf("Camera", "Coach"), selectedIndex = if (showDemo) 1 else 0, onSelect = { onDemo(it == 1) }, compact = true)
                if (!showDemo) TextButton(onClick = onFlip, modifier = Modifier.heightIn(min = 48.dp)) { Text("Flip camera", color = Color.White) }
            }
            TextButton(
                onClick = { onVoiceCuesChange(!voiceCues) },
                modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = if (voiceCues) "Voice coach on, tap to mute" else "Voice coach muted, tap to turn on" },
            ) { Text(if (voiceCues) "Voice on" else "Voice muted", color = if (voiceCues) Color.White else MfColors.OnNightMuted) }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.Bottom) {
            RoundAction("■", "End", onClick = { viewModel.onEvent(SessionEvent.Stop) }, content = MfColors.Cue)
            RoundAction("▶", "Resume", onClick = { viewModel.onEvent(SessionEvent.Resume) }, container = MfColors.Yellow, content = Color.Black, size = 84.dp)
            RoundAction("⏭", if (step is SessionStep.Rest) "Skip rest" else "Skip", onClick = { viewModel.onEvent(SessionEvent.Skip) })
        }
    }
}

// ----------------------------------------------------------------------------- summary

@Composable
private fun SummaryStage(
    state: SessionState,
    save: SaveState,
    coach: Coach,
    plate: List<eu.motionforge.app.core.pose.PoseFrame>,
    exercisesById: Map<String, Exercise>,
    onSave: (Int?) -> Unit,
    onClose: () -> Unit,
    onOpenProgress: () -> Unit,
) {
    var effort by rememberSaveable { mutableIntStateOf(0) }
    val reps = state.results.mapNotNull { it.repetitions }
    val context = LocalContext.current
    BackHandler(onBack = onClose)
    val stats = buildList {
        add(formatClock(state.workSeconds) + " active")
        add("${state.results.size} exercise${if (state.results.size == 1) "" else "s"}")
        if (reps.isNotEmpty()) add("${reps.sum()} reps")
    }.joinToString(", ")

    ScreenColumn(title = if (state.endedEarly) "Session ended" else "Session complete") {
        Box(Modifier.fillMaxWidth().height(360.dp).clip(PlateShape).background(MfColors.Plate)) {
            if (plate.isNotEmpty()) {
                SessionPlateCanvas(plate, Modifier.fillMaxSize().padding(bottom = 24.dp))
            } else {
                val last = state.results.lastOrNull()?.exerciseId ?: (state.plan.steps.first { it is SessionStep.Work } as SessionStep.Work).exerciseId
                MotionStudy(coach.studyArt(last), Modifier.fillMaxSize())
            }
            MeasureScale(Modifier.align(Alignment.BottomCenter).padding(horizontal = 14.dp, vertical = 10.dp), color = Color.White.copy(alpha = 0.5f))
        }
        Text(
            if (plate.isNotEmpty()) "Your last reps, drawn from body points only. No photos were kept."
            else "Turn on the camera next time to get a plate of your own movement.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (plate.isNotEmpty()) {
            SecondaryButton("Share your plate", onClick = { shareSessionPlate(context, plate, state.plan.title, stats) })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile(formatClock(state.workSeconds), "Active time", Modifier.weight(1f))
            StatTile("${state.results.size}", "Exercises", Modifier.weight(1f))
            if (reps.isNotEmpty()) StatTile("${reps.sum()}", "Reps", Modifier.weight(1f))
        }
        if (state.results.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                eu.motionforge.app.core.design.SectionHeader("What you did")
                state.results.forEach { r ->
                    val repText = r.repetitions?.let { ", $it reps (experimental count)" }.orEmpty()
                    Text("${r.name}, ${formatClock(r.elapsedSeconds)}$repText", style = MaterialTheme.typography.bodyLarge)
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
                eu.motionforge.app.core.design.SectionHeader("How hard did it feel?")
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    (1..10).forEach { n -> EffortChip(n, effort == n) { effort = if (effort == n) 0 else n } }
                }
                Text("Optional. 1 is very easy, 10 is maximum effort.", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (save == SaveState.FAILED) Text("Saving failed. Please try again.", color = MfColors.Halt)
                PrimaryButton(if (save == SaveState.SAVING) "Saving…" else "Save session", onClick = { onSave(effort.takeIf { it in 1..10 }) }, enabled = save != SaveState.SAVING)
                TextButton(onClick = onClose, modifier = Modifier.fillMaxWidth()) { Text("Discard") }
            }
        }
    }
}

/** Live coaching over the camera (squat and boxing checks). Always labelled experimental; never certifies technique. */
@Composable
private fun CoachingCard(c: LiveCoaching, modifier: Modifier = Modifier) {
    val color = when (c.tone) {
        CoachTone.PAUSED, CoachTone.NEUTRAL -> MfColors.OnNightMuted
        CoachTone.GOOD -> MfColors.SignalOnNight
        CoachTone.ADJUST -> MfColors.Cue
    }
    Surface(
        modifier = modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite },
        shape = PlateShape,
        color = MfColors.Night.copy(alpha = 0.86f),
    ) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.Top) {
            Box(Modifier.padding(top = 4.dp).width(4.dp).height(36.dp).background(color))
            Spacer(Modifier.width(10.dp))
            Column {
                Text(c.title, style = MaterialTheme.typography.labelLarge, color = color)
                Text(c.message, style = MaterialTheme.typography.titleMedium, color = MfColors.OnNight)
            }
        }
    }
}

@Composable
private fun EffortChip(n: Int, selected: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier
            .size(48.dp)
            .selectable(selected = selected, onClick = onClick, role = Role.RadioButton)
            .semantics { contentDescription = "Effort $n of 10" },
        shape = PlateShape,
        color = if (selected) MfColors.Ink else MaterialTheme.colorScheme.surfaceContainer,
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text("$n", style = MfType.NumeralSmall, color = if (selected) Color.White else MfColors.Ink)
        }
    }
}
