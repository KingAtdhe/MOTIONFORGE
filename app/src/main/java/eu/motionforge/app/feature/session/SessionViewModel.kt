package eu.motionforge.app.feature.session

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import eu.motionforge.app.core.movement.SquatRepCounter
import eu.motionforge.app.core.pose.PoseOutput
import eu.motionforge.app.core.pose.TrackingState
import eu.motionforge.app.core.pose.TrackingStateEvaluator
import eu.motionforge.app.data.SessionRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

enum class SaveState { IDLE, SAVING, SAVED, FAILED }

class SessionViewModel(plan: SessionPlan, private val repository: SessionRepository) : ViewModel() {

    private val _state = MutableStateFlow(SessionState(plan))
    val state: StateFlow<SessionState> = _state.asStateFlow()

    private val _tracking = MutableStateFlow(TrackingState.CAMERA_INITIALIZING)
    val tracking: StateFlow<TrackingState> = _tracking.asStateFlow()

    private val _save = MutableStateFlow(SaveState.IDLE)
    val save: StateFlow<SaveState> = _save.asStateFlow()

    private val evaluator = TrackingStateEvaluator(TrackingStateEvaluator.FULL_BODY)
    private val repCounter = SquatRepCounter()
    private var startedAtMillis = 0L
    private var ticker: Job? = null

    fun onEvent(event: SessionEvent) {
        val before = _state.value
        val after = SessionEngine.reduce(before, event)
        _state.value = after
        if (event is SessionEvent.Start && after.phase == SessionPhase.RUNNING) startedAtMillis = System.currentTimeMillis()
        // A repetition may never span a step change or a pause.
        if (after.stepIndex != before.stepIndex || after.phase != SessionPhase.RUNNING) repCounter.reset()
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

    /** Pose results from the camera (main thread). */
    fun onPose(output: PoseOutput) {
        val trackingState = evaluator.update(output)
        _tracking.value = trackingState
        val s = _state.value
        val step = s.currentStep
        if (s.phase == SessionPhase.RUNNING && step is SessionStep.Work && step.countsReps && output is PoseOutput.Detected) {
            val before = repCounter.repetitions
            repCounter.update(output.frame, tracking = trackingState.allowsFeedback)
            if (repCounter.repetitions > before) onEvent(SessionEvent.RepCounted)
        }
    }

    fun onCameraHidden() {
        evaluator.reset()
        repCounter.reset()
        _tracking.value = TrackingState.PAUSED
    }

    fun saveSession(perceivedEffort: Int?) {
        val s = _state.value
        if (!s.isSaveable || _save.value == SaveState.SAVING || _save.value == SaveState.SAVED) return
        _save.value = SaveState.SAVING
        viewModelScope.launch {
            _save.value = runCatching {
                repository.save(s, startedAtMillis, System.currentTimeMillis(), perceivedEffort)
            }.fold({ SaveState.SAVED }, { SaveState.FAILED })
        }
    }
}
