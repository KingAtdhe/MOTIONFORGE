package eu.motionforge.app.feature.session

import eu.motionforge.app.core.coaching.CuePriority
import eu.motionforge.app.core.coaching.VoiceCoach
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.core.movement.FormFeedback
import eu.motionforge.app.core.movement.JabResult
import eu.motionforge.app.core.movement.SquatEvent

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
                camera && step.formDrill != null -> " I'll watch your guard."
                else -> ""
            }
            CoachLine("${step.name}. ${step.durationSeconds} seconds.$extra", CuePriority.ANNOUNCE)
        }
        is SessionStep.Rest -> CoachLine("Rest. Next up: ${step.nextName}.", CuePriority.ANNOUNCE)
    }

    fun squatLine(event: SquatEvent): CoachLine = when (event) {
        is SquatEvent.RepCompleted -> {
            val n = VoiceCoach.count(event.rep)
            val issue = event.issues.minByOrNull { it.ordinal }
            if (issue != null) CoachLine("$n ${issue.spoken}", CuePriority.CORRECTION)
            else CoachLine("$n ${VoiceCoach.praise(event.rep)}", CuePriority.COUNT)
        }
        SquatEvent.ShallowRep -> CoachLine(SHALLOW, CuePriority.CORRECTION)
    }

    fun squatCard(event: SquatEvent?, tracking: Boolean): LiveCoaching = when {
        !tracking -> LiveCoaching("Squat check paused", "Keep your whole body in view, side-on or facing the phone.", CoachTone.PAUSED)
        event == null -> LiveCoaching("Squat check (experimental)", "Lower with control. Each rep is checked when you stand up.", CoachTone.NEUTRAL)
        event is SquatEvent.ShallowRep -> LiveCoaching("Not counted", "That dip didn't reach counting depth. Go a little lower if it's comfortable.", CoachTone.ADJUST)
        event is SquatEvent.RepCompleted && event.issues.isEmpty() ->
            LiveCoaching("Rep ${event.rep}", "No adjustments spotted on that rep. Keep it up.", CoachTone.GOOD)
        else -> {
            val rep = event as SquatEvent.RepCompleted
            LiveCoaching("Rep ${rep.rep}", rep.issues.sortedBy { it.ordinal }.joinToString("\n") { it.message }, CoachTone.ADJUST)
        }
    }

    /** Spoken line for a finished jab: only clean ones are praised (faults already have their own cue). */
    fun jabLine(result: JabResult): CoachLine? = if (result.clean) CoachLine(GOOD_JAB, CuePriority.PRAISE) else null

    /** Spoken line when the boxing form state changes to a new cue. */
    fun formLine(previous: FormFeedback?, now: FormFeedback): CoachLine? {
        if (now !is FormFeedback.Cue) return null
        if (previous is FormFeedback.Cue && previous.issue == now.issue) return null
        return CoachLine(now.issue.spoken, CuePriority.CORRECTION)
    }

    fun boxingCard(form: FormFeedback, drill: BoxingDrill, cleanJabs: Int): LiveCoaching {
        val title = if (drill == BoxingDrill.JAB) "Form check (experimental) · ${form.jabs} jabs, $cleanJabs clean" else "Form check (experimental)"
        return when (form) {
            is FormFeedback.NotAssessing -> LiveCoaching(title, "Form check paused — keep your whole body, hands and feet in view.", CoachTone.PAUSED)
            is FormFeedback.Steady -> LiveCoaching(title, "No adjustments spotted. Keep it up.", CoachTone.GOOD)
            is FormFeedback.Cue -> LiveCoaching(title, form.issue.message, CoachTone.ADJUST)
        }
    }
}
