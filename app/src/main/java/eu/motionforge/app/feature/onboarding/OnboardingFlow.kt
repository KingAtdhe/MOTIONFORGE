package eu.motionforge.app.feature.onboarding

import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal

enum class OnboardingStep { WELCOME, AGE, UNDER_AGE, SAFETY, FOCUS, GOAL, COACH }

/** Answer to "are you a woman or a man?" — used only to pick the matching coach; the answer itself is not stored. */
enum class GenderAnswer(val label: String, val coach: Coach) {
    WOMAN("Woman", Coach.FEMALE),
    MAN("Man", Coach.MALE),
    NOT_SAID("Prefer not to say", Coach.DEFAULT),
}

/**
 * Onboarding state machine (pure, unit-tested).
 *
 * Order: WELCOME → AGE → SAFETY → FOCUS → GOAL → COACH → done.
 * The gender answer only selects the coach; only the coach is persisted.
 * Declaring under 18 leads to UNDER_AGE, which can only go back to AGE: the MVP is adults-only.
 * The age answer itself is never stored; only "onboarding completed" is persisted.
 */
data class OnboardingState(
    val step: OnboardingStep = OnboardingStep.WELCOME,
    val safetyAcknowledged: Boolean = false,
    val focus: TrainingCategory? = null,
    val goal: TrainingGoal? = null,
    val gender: GenderAnswer? = null,
) {
    val coach: Coach get() = gender?.coach ?: Coach.DEFAULT

    val canContinue: Boolean
        get() = when (step) {
            OnboardingStep.WELCOME -> true
            OnboardingStep.AGE, OnboardingStep.UNDER_AGE -> false // answered with explicit buttons
            OnboardingStep.SAFETY -> safetyAcknowledged
            OnboardingStep.FOCUS -> focus != null
            OnboardingStep.GOAL -> goal != null
            OnboardingStep.COACH -> gender != null
        }

    val isFinalStep: Boolean get() = step == OnboardingStep.COACH

    /** 1-based progress for the visible steps (UNDER_AGE counts as the age step). */
    val progressIndex: Int
        get() = when (step) {
            OnboardingStep.WELCOME -> 1
            OnboardingStep.AGE, OnboardingStep.UNDER_AGE -> 2
            OnboardingStep.SAFETY -> 3
            OnboardingStep.FOCUS -> 4
            OnboardingStep.GOAL -> 5
            OnboardingStep.COACH -> 6
        }

    companion object {
        const val VISIBLE_STEPS = 6
    }
}

sealed interface OnboardingEvent {
    data object Continue : OnboardingEvent
    data object Back : OnboardingEvent
    data class AgeAnswered(val isAdult: Boolean) : OnboardingEvent
    data class SafetyAcknowledged(val acknowledged: Boolean) : OnboardingEvent
    data class FocusChosen(val focus: TrainingCategory) : OnboardingEvent
    data class GoalChosen(val goal: TrainingGoal) : OnboardingEvent
    data class GenderChosen(val gender: GenderAnswer) : OnboardingEvent
}

/** Result of a reduction: the new state, and whether onboarding has just finished. */
data class OnboardingTransition(val state: OnboardingState, val completed: Boolean = false)

object OnboardingReducer {

    fun reduce(state: OnboardingState, event: OnboardingEvent): OnboardingTransition = when (event) {
        OnboardingEvent.Continue -> when {
            !state.canContinue -> OnboardingTransition(state)
            state.step == OnboardingStep.WELCOME -> OnboardingTransition(state.copy(step = OnboardingStep.AGE))
            state.step == OnboardingStep.SAFETY -> OnboardingTransition(state.copy(step = OnboardingStep.FOCUS))
            state.step == OnboardingStep.FOCUS -> OnboardingTransition(state.copy(step = OnboardingStep.GOAL))
            state.step == OnboardingStep.GOAL -> OnboardingTransition(state.copy(step = OnboardingStep.COACH))
            state.step == OnboardingStep.COACH -> OnboardingTransition(state, completed = true)
            else -> OnboardingTransition(state)
        }

        OnboardingEvent.Back -> OnboardingTransition(
            state.copy(
                step = when (state.step) {
                    OnboardingStep.WELCOME -> OnboardingStep.WELCOME
                    OnboardingStep.AGE -> OnboardingStep.WELCOME
                    OnboardingStep.UNDER_AGE -> OnboardingStep.AGE
                    OnboardingStep.SAFETY -> OnboardingStep.AGE
                    OnboardingStep.FOCUS -> OnboardingStep.SAFETY
                    OnboardingStep.GOAL -> OnboardingStep.FOCUS
                    OnboardingStep.COACH -> OnboardingStep.GOAL
                },
            ),
        )

        is OnboardingEvent.AgeAnswered -> {
            if (state.step != OnboardingStep.AGE) {
                OnboardingTransition(state)
            } else {
                OnboardingTransition(state.copy(step = if (event.isAdult) OnboardingStep.SAFETY else OnboardingStep.UNDER_AGE))
            }
        }

        is OnboardingEvent.SafetyAcknowledged -> OnboardingTransition(state.copy(safetyAcknowledged = event.acknowledged))
        is OnboardingEvent.FocusChosen -> OnboardingTransition(state.copy(focus = event.focus))
        is OnboardingEvent.GoalChosen -> OnboardingTransition(state.copy(goal = event.goal))
        is OnboardingEvent.GenderChosen -> OnboardingTransition(state.copy(gender = event.gender))
    }
}
