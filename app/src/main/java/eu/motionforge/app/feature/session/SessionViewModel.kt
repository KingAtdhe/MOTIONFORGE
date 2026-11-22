package eu.motionforge.app.feature.session

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import eu.motionforge.app.core.coaching.Utterance
import eu.motionforge.app.core.coaching.VoiceCoach
import eu.motionforge.app.core.movement.BoxingFormMonitor
import eu.motionforge.app.core.movement.RepEvent
import eu.motionforge.app.core.movement.FormFeedback
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.core.movement.RepCounter
import eu.motionforge.app.core.pose.PoseOutput
import eu.motionforge.app.core.pose.TrackingState
import eu.motionforge.app.core.pose.TrackingStateEvaluator
import eu.motionforge.app.data.SessionRepository
import eu.motionforge.app.data.ActiveSessionStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class SaveState { IDLE, SAVING, SAVED, FAILED }

/**
 * @param restored an unfinished session for the same [planKey] read back from [store] (Android closed the app
 *   mid-workout); it continues paused, with everything done so far kept.
 * @param tips each lesson's written cues by exercise id, read out by the voice coach on steps without camera feedback.
 * @param clock milliseconds for pacing the voice coach (monotonic in the app).
 */
class SessionViewModel(
    plan: SessionPlan,
    private val repository: SessionRepository,
    private val store: ActiveSessionStore,
    private val planKey: String,
    restored: SessionSnapshot? = null,
    private val tips: Map<String, List<String>> = emptyMap(),
    private val clock: () -> Long = { android.os.SystemClock.elapsedRealtime() },
) : ViewModel() {

    private val _state = MutableStateFlow(restored?.restoredState() ?: SessionState(plan))
    val state: StateFlow<SessionState> = _state.asStateFlow()

    private val _tracking = MutableStateFlow(TrackingState.CAMERA_INITIALIZING)
    val tracking: StateFlow<TrackingState> = _tracking.asStateFlow()

    private val _save = MutableStateFlow(SaveState.IDLE)
    val save: StateFlow<SaveState> = _save.asStateFlow()

    private val evaluator = TrackingStateEvaluator(TrackingStateEvaluator.FULL_BODY, eitherSide = true)
    /** The rep counter for the current step (squat, push-up or lunge rules), or null when the step isn't counted. */
    private var repCounter: RepCounter? = null
    private var countedMove: CountedMove? = null

    private val _form = MutableStateFlow<FormFeedback?>(null)
    /** Boxing form cues for the current step (null when the step has no form check). */
    val form: StateFlow<FormFeedback?> = _form.asStateFlow()
    private var formMonitor: BoxingFormMonitor? = null

    private val _coaching = MutableStateFlow<LiveCoaching?>(null)
    /** The coaching card for the current camera step (squat or boxing checks), or null. */
    val coaching: StateFlow<LiveCoaching?> = _coaching.asStateFlow()

    private val voice = VoiceCoach()
    private val _speech = MutableSharedFlow<Utterance>(extraBufferCapacity = 8)
    /** Lines for the text-to-speech engine; the screen speaks them when voice cues are on. */
    val speech: SharedFlow<Utterance> = _speech.asSharedFlow()
    private var lastRepEvent: RepEvent? = null
    private var steadySinceMs = -1L
    private var stancePraised = false
    private var startedAtMillis = restored?.startedAtMillis ?: 0L
    private var ticker: Job? = null

    /** True when this screen picked up a session Android had closed; the UI says so once. */
    val wasRestored: Boolean = restored != null

    // Latest state to keep on disk (null = remove). One collector writes in order; a newer value replaces an
    // unwritten older one, so ticking never queues up file writes.
    private sealed interface Disk {
        data object Idle : Disk
        data object Forget : Disk
        data class Keep(val state: SessionState) : Disk
    }
    private val epoch = store.epoch
    private val toPersist = MutableStateFlow<Disk>(restored?.let { Disk.Keep(it.restoredState()) } ?: Disk.Idle)

    init {
        viewModelScope.launch(Dispatchers.IO) {
            toPersist.collectLatest { d ->
                runCatching {
                    when (d) {
                        Disk.Idle -> Unit
                        Disk.Forget -> store.clear()
                        is Disk.Keep -> store.write(SessionSnapshot(planKey, d.state, startedAtMillis, System.currentTimeMillis()), epoch)
                    }
                }
            }
        }
    }

    /** The person closed the summary (saved, discarded or nothing to save): forget the unfinished session. */
    fun onClosed() {
        toPersist.value = Disk.Forget
        store.clear() // synchronous: the screen is about to go away and with it this ViewModel's scope
    }

    fun onEvent(event: SessionEvent) {
        val before = _state.value
        val after = SessionEngine.reduce(before, event)
        _state.value = after
        if (event is SessionEvent.Start && after.phase == SessionPhase.RUNNING) startedAtMillis = System.currentTimeMillis()
        // A repetition may never span a step change or a pause.
        val workId = (after.currentStep as? SessionStep.Work)?.takeIf { it.countsReps }?.exerciseId
        if (after.stepIndex != before.stepIndex || (workId != null && repCounter == null)) {
            countedMove = workId?.let { CountedMove.forExercise(it) }
            repCounter = workId?.let { CountedMove.counterFor(it) }
            lastRepEvent = null
        }
        if (after.stepIndex != before.stepIndex || after.phase != SessionPhase.RUNNING) repCounter?.reset()
        val drill = (after.currentStep as? SessionStep.Work)?.formDrill
        if (after.stepIndex != before.stepIndex || (drill != null && formMonitor == null)) {
            formMonitor = drill?.let { BoxingFormMonitor(it) }
            _form.value = drill?.let { FormFeedback.NotAssessing(0) }
            lastRepEvent = null
            steadySinceMs = -1L
            stancePraised = false
        }
        if (after.phase != SessionPhase.RUNNING) formMonitor?.reset()
        refreshCoachingCard(after)
        val step = after.currentStep
        val live = after.cameraUsed && step is SessionStep.Work && (step.countsReps || step.formDrill != null)
        SessionNarrator.onTransition(before, after, tips, live).forEach(::say)
        if (after.phase != SessionPhase.READY && after != before && toPersist.value != Disk.Forget) toPersist.value = Disk.Keep(after)
        syncTicker(after.phase)
    }

    private fun syncTicker(phase: SessionPhase) {
        if (phase == SessionPhase.RUNNING) {
            if (ticker?.isActive != true) {
                ticker = viewModelScope.launch {
                    while (isActive) {
                        delay(1000)
                        val s = _state.value
                        if (s.phase != SessionPhase.RUNNING) break
                        onEvent(SessionEvent.Tick(tracking = s.cameraUsed && _tracking.value.allowsFeedback))
                    }
                }
            }
        } else {
            ticker?.cancel()
            ticker = null
        }
    }

    // The last few seconds of steadily tracked body points, kept in memory only, for the session plate.
    private val trail = ArrayDeque<eu.motionforge.app.core.pose.PoseFrame>()
    private var lastTrailMs = 0L

    /** Up to [count] evenly spaced poses from the last tracked seconds of work (empty without the camera). */
    fun plateFrames(count: Int = 8): List<eu.motionforge.app.core.pose.PoseFrame> {
        if (trail.size < 4) return emptyList()
        val n = minOf(count, trail.size)
        return List(n) { i -> trail[i * (trail.size - 1) / (n - 1).coerceAtLeast(1)] }
    }

    /** Pose results from the camera (main thread). */
    fun onPose(output: PoseOutput) {
        val trackingState = evaluator.update(output)
        _tracking.value = trackingState
        val now = clock()
        if (output is PoseOutput.Detected && trackingState.allowsFeedback && _state.value.phase == SessionPhase.RUNNING &&
            _state.value.currentStep is SessionStep.Work && now - lastTrailMs >= 160
        ) {
            lastTrailMs = now
            trail.addLast(output.frame)
            while (trail.size > 24) trail.removeFirst()
        }
        val s = _state.value
        val step = s.currentStep
        val counter = repCounter
        if (counter != null && s.phase == SessionPhase.RUNNING && step is SessionStep.Work && step.countsReps && output is PoseOutput.Detected) {
            val before = counter.repetitions
            val update = counter.update(output.frame, tracking = trackingState.allowsFeedback)
            update.event?.let { ev ->
                lastRepEvent = ev
                say(SessionNarrator.repLine(ev))
            }
            if (counter.repetitions > before) onEvent(SessionEvent.RepCounted)
        }
        val monitor = formMonitor
        if (monitor != null && s.phase == SessionPhase.RUNNING && step is SessionStep.Work && step.formDrill != null) {
            val previous = _form.value
            val now = when (output) {
                is PoseOutput.Detected -> monitor.update(output.frame, tracking = trackingState.allowsFeedback)
                else -> FormFeedback.NotAssessing(monitor.jabs)
            }
            _form.value = now
            SessionNarrator.formLine(previous, now)?.let(::say)
            monitor.drainJabs().forEach { r -> SessionNarrator.jabLine(r, step.formDrill)?.let(::say) }
            // a steady, cue-free stance for a few seconds earns one spoken confirmation per step
            val t = clock()
            if (now is FormFeedback.Steady) {
                if (steadySinceMs < 0) steadySinceMs = t
                if (step.formDrill == eu.motionforge.app.core.movement.BoxingDrill.STANCE && !stancePraised &&
                    t - steadySinceMs >= SessionNarrator.STANCE_PRAISE_AFTER_MS
                ) {
                    stancePraised = true
                    say(CoachLine(SessionNarrator.STANCE_PRAISE, eu.motionforge.app.core.coaching.CuePriority.PRAISE))
                }
            } else {
                steadySinceMs = -1L
                if (now is FormFeedback.Cue) stancePraised = false
            }
        }
        refreshCoachingCard(s)
    }

    private fun refreshCoachingCard(s: SessionState) {
        val step = s.currentStep as? SessionStep.Work
        val drill = step?.formDrill
        _coaching.value = when {
            step == null || !s.cameraUsed -> null
            drill != null -> _form.value?.let { SessionNarrator.boxingCard(it, drill, formMonitor?.goodJabs ?: 0) }
            step.countsReps -> SessionNarrator.repCard(countedMove ?: CountedMove.SQUAT, lastRepEvent, _tracking.value.allowsFeedback)
            else -> null
        }
    }

    private fun say(line: CoachLine) {
        voice.offer(line.text, line.priority, clock())?.let { _speech.tryEmit(it) }
    }

    fun onCameraHidden() {
        evaluator.reset()
        repCounter?.reset()
        formMonitor?.reset()
        if (_form.value != null) _form.value = FormFeedback.NotAssessing(formMonitor?.jabs ?: 0)
        _tracking.value = TrackingState.PAUSED
        refreshCoachingCard(_state.value)
    }

    fun saveSession(perceivedEffort: Int?) {
        val s = _state.value
        if (!s.isSaveable || _save.value == SaveState.SAVING || _save.value == SaveState.SAVED) return
        _save.value = SaveState.SAVING
        viewModelScope.launch {
            _save.value = runCatching {
                repository.save(s, startedAtMillis, System.currentTimeMillis(), perceivedEffort)
            }.fold({
                toPersist.value = Disk.Forget
                withContext(Dispatchers.IO) { store.clear() }
                SaveState.SAVED
            }, { SaveState.FAILED })
        }
    }
}
