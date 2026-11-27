package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.core.movement.HoldCheck
import eu.motionforge.app.core.model.TrainingCategory

sealed interface SessionStep {
    val durationSeconds: Int

    data class Work(
        val exerciseId: String,
        val name: String,
        override val durationSeconds: Int,
        /** True for movements the camera can count (squats, push-ups, lunges: see [CountedMove]). */
        val countsReps: Boolean,
        /** Rule-based boxing form cues for this step (camera only), or null. */
        val formDrill: BoxingDrill? = null,
        /** Training-plan rep target: with the camera counting, the step ends when it is reached ([durationSeconds]
         *  is then the time cap). Without the camera it is shown as guidance. */
        val targetReps: Int? = null,
        /** Held-position check for this step (plank, wall sit...; camera only), or null. */
        val holdCheck: HoldCheck? = null,
        /** Shadow-boxing round number (a bell rings at its start and end), or null for an ordinary step. */
        val round: Int? = null,
        /** Combinations the coach calls out during a round, in order, one every [callEverySeconds]. */
        val calls: List<String> = emptyList(),
        val callEverySeconds: Int = 0,
    ) : SessionStep {
        /** The camera gives this step live feedback (counting, a hold check or the guard check). */
        val liveChecked: Boolean get() = countsReps || formDrill != null || holdCheck != null

        /** The call to show [elapsed] seconds into the step (the latest one made), or null before the first. */
        fun callAt(elapsed: Int): String? {
            if (calls.isEmpty() || callEverySeconds <= 0 || elapsed < FIRST_CALL_SECOND) return null
            return calls[((elapsed - FIRST_CALL_SECOND) / callEverySeconds) % calls.size]
        }

        /** True on the second a new call is made (none in the last few seconds of the round). */
        fun callsAt(elapsed: Int): Boolean =
            calls.isNotEmpty() && callEverySeconds > 0 && elapsed >= FIRST_CALL_SECOND &&
                (elapsed - FIRST_CALL_SECOND) % callEverySeconds == 0 && durationSeconds - elapsed > 3

        companion object {
            /** Seconds into a round before the first call: time to settle into the stance after the bell. */
            const val FIRST_CALL_SECOND = 5
        }
    }

    data class Rest(override val durationSeconds: Int, val nextName: String) : SessionStep
}

data class SessionPlan(val title: String, val type: TrainingCategory, val steps: List<SessionStep>) {
    init {
        require(steps.any { it is SessionStep.Work }) { "A session needs at least one exercise" }
        require(steps.all { it.durationSeconds > 0 }) { "Step durations must be positive" }
    }

    val totalSeconds: Int get() = steps.sumOf { it.durationSeconds }
    val workCount: Int get() = steps.count { it is SessionStep.Work }
}

object SessionPlanner {
    const val REST_SECONDS = 15
    const val SQUAT_ID = "bodyweight_squat"
    private const val WARM_UP_ID = "standing_mobility_warmup"
    private const val MAX_QUICK_EXERCISES = 4

    const val STANCE_ID = "boxing_stance"
    const val JAB_ID = "boxing_jab"
    const val CROSS_ID = "boxing_cross"

    fun drillFor(id: String): BoxingDrill? = when (id) {
        STANCE_ID -> BoxingDrill.STANCE; JAB_ID -> BoxingDrill.JAB; CROSS_ID -> BoxingDrill.CROSS
        else -> if (id in BoxingDrill.GUARD_CHECKED) BoxingDrill.STANCE else null
    }

    private fun work(e: Exercise) = SessionStep.Work(
        e.id, e.name, e.durationSeconds, countsReps = CountedMove.forExercise(e.id) != null, formDrill = drillFor(e.id),
        holdCheck = HoldCheck.forExercise(e.id),
    )

    fun single(exercise: Exercise) = SessionPlan(exercise.name, exercise.category, listOf(work(exercise)))

    /** Short guided session: warm-up first (when the pool has one), then lessons in catalogue order, with rests. */
    fun quick(catalog: List<Exercise>, focus: TrainingCategory?): SessionPlan? {
        val category = focus ?: TrainingCategory.FITNESS
        // the quick session never assumes equipment
        val pool = catalog.filter { it.category == category && !it.needsEquipment }.ifEmpty { catalog.filter { !it.needsEquipment } }
        if (pool.isEmpty()) return null
        val warmUp = catalog.firstOrNull { it.id == WARM_UP_ID }
        val picked = (listOfNotNull(warmUp) + pool.filter { it.id != WARM_UP_ID }).take(MAX_QUICK_EXERCISES)
        val steps = buildList {
            picked.forEachIndexed { i, e ->
                if (i > 0) add(SessionStep.Rest(REST_SECONDS, e.name))
                add(work(e))
            }
        }
        return SessionPlan("Short ${category.displayName.lowercase()} session", category, steps)
    }
}

enum class SessionPhase { READY, RUNNING, PAUSED, FINISHED }

enum class TrackingQuality(val wireName: String) {
    GOOD("good"), PARTIAL("partial"), UNAVAILABLE("unavailable"), NOT_USED("not_used");

    companion object {
        fun of(cameraUsed: Boolean, trackedSeconds: Int, elapsedSeconds: Int): TrackingQuality = when {
            !cameraUsed -> NOT_USED
            elapsedSeconds <= 0 -> UNAVAILABLE
            trackedSeconds >= elapsedSeconds * 0.7 -> GOOD
            trackedSeconds >= elapsedSeconds * 0.3 -> PARTIAL
            else -> UNAVAILABLE
        }
    }
}

data class StepResult(
    val exerciseId: String,
    val name: String,
    val sequence: Int,
    val elapsedSeconds: Int,
    /** Null whenever the count is not trustworthy (no rule, no camera, or tracking mostly unavailable). */
    val repetitions: Int?,
    val trackingQuality: TrackingQuality,
    /** The plan's rep target for this step, if any. */
    val targetReps: Int? = null,
    /** Seconds held in position (hold checks), null when not measured or tracking was mostly unavailable. */
    val heldSeconds: Int? = null,
)

data class SessionState(
    val plan: SessionPlan,
    val cameraUsed: Boolean = false,
    val phase: SessionPhase = SessionPhase.READY,
    val stepIndex: Int = 0,
    val remainingInStep: Int = plan.steps.first().durationSeconds,
    val elapsedTotal: Int = 0,
    val stepElapsed: Int = 0,
    val stepTracked: Int = 0,
    val stepReps: Int = 0,
    /** Whole seconds held in position in the current step (hold checks; camera only). */
    val stepHeld: Int = 0,
    val results: List<StepResult> = emptyList(),
    val endedEarly: Boolean = false,
) {
    val currentStep: SessionStep get() = plan.steps[stepIndex.coerceAtMost(plan.steps.lastIndex)]
    val workSeconds: Int get() = results.sumOf { it.elapsedSeconds }

    /** Sessions with almost no exercise time are not worth recording. */
    val isSaveable: Boolean get() = phase == SessionPhase.FINISHED && workSeconds >= MIN_SAVEABLE_SECONDS
    val workIndex: Int get() = plan.steps.take(stepIndex + 1).count { it is SessionStep.Work }

    companion object {
        const val MIN_SAVEABLE_SECONDS = 10
    }
}

sealed interface SessionEvent {
    data class Start(val cameraUsed: Boolean) : SessionEvent

    /** One second passed. [tracking] = pose tracking was in TRACKING state during it. */
    data class Tick(val tracking: Boolean) : SessionEvent
    data object Pause : SessionEvent
    data object Resume : SessionEvent
    data object Skip : SessionEvent
    data object Stop : SessionEvent
    data object RepCounted : SessionEvent

    /** The hold check has seen [seconds] whole seconds in position in this step (never decreases). */
    data class HoldProgress(val seconds: Int) : SessionEvent
}

/** Pure session state machine: timer, step sequence, rests, pause/skip/stop, per-exercise results. */
object SessionEngine {

    fun reduce(s: SessionState, e: SessionEvent): SessionState = when (e) {
        is SessionEvent.Start -> if (s.phase == SessionPhase.READY) s.copy(phase = SessionPhase.RUNNING, cameraUsed = e.cameraUsed) else s
        SessionEvent.Pause -> if (s.phase == SessionPhase.RUNNING) s.copy(phase = SessionPhase.PAUSED) else s
        SessionEvent.Resume -> if (s.phase == SessionPhase.PAUSED) s.copy(phase = SessionPhase.RUNNING) else s
        SessionEvent.RepCounted -> {
            val step = s.currentStep
            if (s.phase == SessionPhase.RUNNING && step is SessionStep.Work && step.countsReps) {
                val counted = s.copy(stepReps = s.stepReps + 1)
                // target reached: the set is done, move on (the time cap no longer matters)
                if (step.targetReps != null && counted.stepReps >= step.targetReps) advance(counted) else counted
            } else s
        }
        is SessionEvent.HoldProgress -> {
            val step = s.currentStep
            if (s.phase == SessionPhase.RUNNING && step is SessionStep.Work && step.holdCheck != null && e.seconds > s.stepHeld) {
                s.copy(stepHeld = minOf(e.seconds, s.stepElapsed + 1))
            } else s
        }
        is SessionEvent.Tick -> if (s.phase != SessionPhase.RUNNING) s else {
            val ticked = s.copy(
                remainingInStep = s.remainingInStep - 1,
                elapsedTotal = s.elapsedTotal + 1,
                stepElapsed = s.stepElapsed + 1,
                stepTracked = s.stepTracked + if (e.tracking) 1 else 0,
            )
            if (ticked.remainingInStep <= 0) advance(ticked) else ticked
        }
        SessionEvent.Skip -> if (s.phase == SessionPhase.RUNNING || s.phase == SessionPhase.PAUSED) advance(s).let {
            if (it.phase == SessionPhase.FINISHED) it else it.copy(phase = SessionPhase.RUNNING)
        } else s
        SessionEvent.Stop -> when (s.phase) {
            SessionPhase.FINISHED -> s
            SessionPhase.READY -> s.copy(phase = SessionPhase.FINISHED, endedEarly = true)
            else -> closeStep(s).copy(phase = SessionPhase.FINISHED, endedEarly = true)
        }
    }

    private fun closeStep(s: SessionState): SessionState {
        val step = s.currentStep
        if (step !is SessionStep.Work || s.stepElapsed <= 0) return s
        val quality = TrackingQuality.of(s.cameraUsed, s.stepTracked, s.stepElapsed)
        val reps = if (step.countsReps && (quality == TrackingQuality.GOOD || quality == TrackingQuality.PARTIAL)) s.stepReps else null
        val held = if (step.holdCheck != null && s.cameraUsed && (quality == TrackingQuality.GOOD || quality == TrackingQuality.PARTIAL)) s.stepHeld else null
        return s.copy(results = s.results + StepResult(step.exerciseId, step.name, s.results.size + 1, s.stepElapsed, reps, quality, step.targetReps, held))
    }

    private fun advance(s: SessionState): SessionState {
        val closed = closeStep(s)
        val next = s.stepIndex + 1
        return if (next >= s.plan.steps.size) {
            closed.copy(phase = SessionPhase.FINISHED, remainingInStep = 0)
        } else {
            closed.copy(stepIndex = next, remainingInStep = s.plan.steps[next].durationSeconds, stepElapsed = 0, stepTracked = 0, stepReps = 0, stepHeld = 0)
        }
    }
}
