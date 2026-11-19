package eu.motionforge.app.feature.onboarding

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OnboardingReducerTest {

    private fun OnboardingState.on(e: OnboardingEvent) = OnboardingReducer.reduce(this, e)

    @Test
    fun happyPathCompletes() {
        var s = OnboardingState()
        s = s.on(OnboardingEvent.Continue).state
        assertEquals(OnboardingStep.AGE, s.step)
        s = s.on(OnboardingEvent.AgeAnswered(isAdult = true)).state
        assertEquals(OnboardingStep.SAFETY, s.step)
        s = s.on(OnboardingEvent.SafetyAcknowledged(true)).state
        s = s.on(OnboardingEvent.Continue).state
        assertEquals(OnboardingStep.FOCUS, s.step)
        s = s.on(OnboardingEvent.FocusChosen(TrainingCategory.FITNESS)).state.on(OnboardingEvent.Continue).state
        assertEquals(OnboardingStep.GOAL, s.step)
        s = s.on(OnboardingEvent.GoalChosen(TrainingGoal.LEARN_BASICS)).state.on(OnboardingEvent.Continue).state
        assertEquals(OnboardingStep.COACH, s.step)
        val t = s.on(OnboardingEvent.GenderChosen(GenderAnswer.MAN)).state.on(OnboardingEvent.Continue)
        assertTrue(t.completed)
        assertEquals(eu.motionforge.app.core.model.Coach.MALE, t.state.coach)
        assertEquals(TrainingCategory.FITNESS, t.state.focus)
        assertEquals(TrainingGoal.LEARN_BASICS, t.state.goal)
    }

    @Test
    fun underAgeCannotProceed() {
        val s = OnboardingState(step = OnboardingStep.AGE).on(OnboardingEvent.AgeAnswered(isAdult = false)).state
        assertEquals(OnboardingStep.UNDER_AGE, s.step)
        assertFalse(s.canContinue)
        val after = s.on(OnboardingEvent.Continue)
        assertEquals(OnboardingStep.UNDER_AGE, after.state.step)
        assertFalse(after.completed)
        assertEquals(OnboardingStep.AGE, s.on(OnboardingEvent.Back).state.step)
    }

    @Test
    fun ageCannotBeSkippedWithContinue() {
        val s = OnboardingState(step = OnboardingStep.AGE).on(OnboardingEvent.Continue).state
        assertEquals(OnboardingStep.AGE, s.step)
    }

    @Test
    fun safetyMustBeAcknowledged() {
        val s = OnboardingState(step = OnboardingStep.SAFETY)
        assertFalse(s.canContinue)
        assertEquals(OnboardingStep.SAFETY, s.on(OnboardingEvent.Continue).state.step)
        val ack = s.on(OnboardingEvent.SafetyAcknowledged(true)).state
        assertTrue(ack.canContinue)
        val unack = ack.on(OnboardingEvent.SafetyAcknowledged(false)).state
        assertFalse(unack.canContinue)
    }

    @Test
    fun focusAndGoalAreRequired() {
        assertFalse(OnboardingState(step = OnboardingStep.FOCUS).canContinue)
        assertFalse(OnboardingState(step = OnboardingStep.GOAL).canContinue)
        assertFalse(OnboardingState(step = OnboardingStep.GOAL).on(OnboardingEvent.Continue).completed)
        assertFalse(OnboardingState(step = OnboardingStep.COACH).canContinue)
        assertFalse(OnboardingState(step = OnboardingStep.COACH).on(OnboardingEvent.Continue).completed)
    }

    @Test
    fun ageAnswerIgnoredOutsideAgeStep() {
        val s = OnboardingState(step = OnboardingStep.WELCOME).on(OnboardingEvent.AgeAnswered(true)).state
        assertEquals(OnboardingStep.WELCOME, s.step)
    }

    @Test
    fun backWalksTheFlow() {
        assertEquals(OnboardingStep.FOCUS, OnboardingState(step = OnboardingStep.GOAL).on(OnboardingEvent.Back).state.step)
        assertEquals(OnboardingStep.GOAL, OnboardingState(step = OnboardingStep.COACH).on(OnboardingEvent.Back).state.step)
        assertEquals(OnboardingStep.WELCOME, OnboardingState().on(OnboardingEvent.Back).state.step)
    }

    @Test
    fun progressCoversAllVisibleSteps() {
        assertEquals(setOf(1, 2, 3, 4, 5, 6), OnboardingStep.entries.map { OnboardingState(step = it).progressIndex }.toSet())
    }

    @Test
    fun genderOnlyPicksTheCoach() {
        assertEquals(eu.motionforge.app.core.model.Coach.FEMALE, OnboardingState(gender = GenderAnswer.WOMAN).coach)
        assertEquals(eu.motionforge.app.core.model.Coach.MALE, OnboardingState(gender = GenderAnswer.MAN).coach)
        assertEquals(eu.motionforge.app.core.model.Coach.DEFAULT, OnboardingState(gender = GenderAnswer.NOT_SAID).coach)
    }
}
