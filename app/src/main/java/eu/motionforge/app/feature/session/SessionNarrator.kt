package eu.motionforge.app.feature.session

import eu.motionforge.app.core.coaching.CuePriority
import eu.motionforge.app.core.coaching.VoiceCoach
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.core.movement.FormFeedback
import eu.motionforge.app.core.movement.HoldCheck
import eu.motionforge.app.core.movement.HoldFeedback
import eu.motionforge.app.core.movement.JabResult
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.core.movement.RepEvent

/** A line the coach would like to say; [VoiceCoach] decides whether it is actually spoken. */
data class CoachLine(val text: String, val priority: CuePriority)

enum class CoachTone { NEUTRAL, GOOD, ADJUST, PAUSED }

/** What the on-screen coaching card shows during a camera step. */
data class LiveCoaching(val title: String, val message: String, val tone: CoachTone)

/**
 * Turns session and movement events into coaching lines and card text. Pure Kotlin, unit-tested.
 * Never certifies technique: positive lines only say that no rule found anything to adjust.
 */
object SessionNarrator {
    /** Seconds between spoken lesson tips on steps without live camera feedback. */
    const val TIP_EVERY_SECONDS = 20

    /** Seconds of steady, cue-free stance before the coach says so. */
    const val STANCE_PRAISE_AFTER_MS = 6_000L

    const val STANCE_PRAISE = "Good stance. Hands up, feet balanced."
    const val GOOD_JAB = "Good jab."
    const val TARGET_REACHED = "Target reached. Well done."
    const val GOOD_CROSS = "Good cross."
    const val SHALLOW = "Not counted. Go a little lower if it's comfortable."

    /**
     * Lines for a state change. [tips] = the lesson's written cues by exercise id;
     * [liveFeedback] = the current step gets rule-based camera feedback, so it does not need spoken tips.
     */
    fun onTransition(before: SessionState, after: SessionState, tips: Map<String, List<String>>, liveFeedback: Boolean): List<CoachLine> {
        if (after.phase == SessionPhase.FINISHED) {
            return if (before.phase == SessionPhase.FINISHED) emptyList()
            else listOf(CoachLine(if (after.endedEarly) "Session ended." else "Session complete. Well done.", CuePriority.ANNOUNCE))
        }
        if (after.phase != SessionPhase.RUNNING) return emptyList()
        val step = after.currentStep
        val started = before.phase == SessionPhase.READY || after.stepIndex != before.stepIndex
        if (started) return listOf(announce(step, after.cameraUsed))
        if (before.phase != SessionPhase.RUNNING || after.stepElapsed == before.stepElapsed) return emptyList()

        val lines = mutableListOf<CoachLine>()
        when (step) {
            is SessionStep.Work -> {
                if (after.remainingInStep == 10 && step.durationSeconds >= 30) lines += CoachLine("Ten seconds left.", CuePriority.COUNT)
                val list = tips[step.exerciseId].orEmpty()
                val e = after.stepElapsed
                if (!liveFeedback && list.isNotEmpty() && e % TIP_EVERY_SECONDS == 8 && after.remainingInStep > 12) {
                    lines += CoachLine(list[(e / TIP_EVERY_SECONDS) % list.size], CuePriority.INFO)
                }
            }
            is SessionStep.Rest -> if (after.remainingInStep == 3) lines += CoachLine("Get ready.", CuePriority.COUNT)
        }
        return lines
    }

    private fun announce(step: SessionStep, camera: Boolean): CoachLine = when (step) {
        is SessionStep.Work -> {
            val extra = when {
                camera && step.countsReps -> " I'll count your reps and check each one."
                camera && step.holdCheck != null -> " I'll time your hold while you're in position."
                camera && step.formDrill != null -> " I'll watch your guard."
                else -> ""
            }
            val what = if (step.targetReps != null && camera && step.countsReps) "${step.targetReps} reps." else "${step.durationSeconds} seconds."
            CoachLine("${step.name}. $what$extra", CuePriority.ANNOUNCE)
        }
        is SessionStep.Rest -> CoachLine("Rest. Next up: ${step.nextName}.", CuePriority.ANNOUNCE)
    }

    fun repLine(event: RepEvent): CoachLine = when (event) {
        is RepEvent.RepCompleted -> {
            val n = VoiceCoach.count(event.rep)
            val issue = event.issues.firstOrNull()
            if (issue != null) CoachLine("$n ${issue.spoken}", CuePriority.CORRECTION)
            else CoachLine("$n ${VoiceCoach.praise(event.rep)}", CuePriority.COUNT)
        }
        RepEvent.ShallowRep -> CoachLine(SHALLOW, CuePriority.CORRECTION)
    }

    fun squatCard(event: RepEvent?, tracking: Boolean): LiveCoaching = repCard(CountedMove.SQUAT, event, tracking)

    fun repCard(move: CountedMove, event: RepEvent?, tracking: Boolean): LiveCoaching = when {
        !tracking -> LiveCoaching("${move.checkName} paused", move.framing, CoachTone.PAUSED)
        event == null -> LiveCoaching("${move.checkName} (experimental)", move.idle, CoachTone.NEUTRAL)
        event is RepEvent.ShallowRep -> LiveCoaching("Not counted", move.shallow, CoachTone.ADJUST)
        event is RepEvent.RepCompleted && event.issues.isEmpty() ->
            LiveCoaching("Rep ${event.rep}", "No adjustments spotted on that rep. Keep it up.", CoachTone.GOOD)
        else -> {
            val rep = event as RepEvent.RepCompleted
            LiveCoaching("Rep ${rep.rep}", rep.issues.joinToString("\n") { it.message }, CoachTone.ADJUST)
        }
    }

    /** Spoken line for a finished jab: only clean ones are praised (faults already have their own cue). */
    fun jabLine(result: JabResult, drill: BoxingDrill = BoxingDrill.JAB): CoachLine? =
        if (result.clean) CoachLine(if (drill == BoxingDrill.CROSS) GOOD_CROSS else GOOD_JAB, CuePriority.PRAISE) else null

    /** Spoken line when the boxing form state changes to a new cue. */
    fun formLine(previous: FormFeedback?, now: FormFeedback): CoachLine? {
        if (now !is FormFeedback.Cue) return null
        if (previous is FormFeedback.Cue && previous.issue == now.issue) return null
        return CoachLine(now.issue.spoken, CuePriority.CORRECTION)
    }

    fun boxingCard(form: FormFeedback, drill: BoxingDrill, cleanJabs: Int, reps: Int? = null): LiveCoaching {
        val title = if (drill == BoxingDrill.JAB) "Form check (experimental) · ${form.jabs} jabs, $cleanJabs clean"
            else if (drill == BoxingDrill.CROSS) "Form check (experimental) · ${form.jabs} crosses, $cleanJabs clean"
            else if (reps != null) "Guard check (experimental) · $reps counted"
            else "Form check (experimental)"
        return when (form) {
            is FormFeedback.NotAssessing -> LiveCoaching(title, "Form check paused — keep your whole body, hands and feet in view.", CoachTone.PAUSED)
            is FormFeedback.Steady -> LiveCoaching(title, "No adjustments spotted. Keep it up.", CoachTone.GOOD)
            is FormFeedback.Cue -> LiveCoaching(title, form.issue.message, CoachTone.ADJUST)
        }
    }

    /** Seconds held, cue-free, before the coach says so once per step. */
    const val HOLD_PRAISE_AFTER_MS = 10_000L
    const val HOLD_PRAISE = "Good. Holding steady."

    /** Spoken line when a hold check changes state: a new adjustment, or losing / finding the position. */
    fun holdLine(previous: HoldFeedback?, now: HoldFeedback): CoachLine? = when {
        now is HoldFeedback.Cue && !(previous is HoldFeedback.Cue && previous.issue == now.issue) -> CoachLine(now.issue.spoken, CuePriority.CORRECTION)
        now is HoldFeedback.OutOfPosition && (previous is HoldFeedback.Holding || previous is HoldFeedback.Cue) ->
            CoachLine("Timer paused. Back into position when you're ready.", CuePriority.INFO)
        else -> null
    }

    fun holdCard(check: HoldCheck, hold: HoldFeedback): LiveCoaching {
        val t = hold.heldMs / 1000
        val title = "${check.checkName} (experimental) · ${t / 60}:${(t % 60).toString().padStart(2, '0')} held"
        return when (hold) {
            is HoldFeedback.NotAssessing -> LiveCoaching(title, "Timer paused — ${check.framing.replaceFirstChar { it.lowercase() }}", CoachTone.PAUSED)
            is HoldFeedback.OutOfPosition -> LiveCoaching(title, check.waiting, CoachTone.NEUTRAL)
            is HoldFeedback.Holding -> LiveCoaching(title, check.holding, CoachTone.GOOD)
            is HoldFeedback.Cue -> LiveCoaching(title, hold.issue.message, CoachTone.ADJUST)
        }
    }
}
