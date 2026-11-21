package eu.motionforge.app.feature.session

import eu.motionforge.app.core.coaching.CuePriority
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.core.movement.FormFeedback
import eu.motionforge.app.core.movement.FormIssue
import eu.motionforge.app.core.movement.JabResult
import eu.motionforge.app.core.movement.SquatEvent
import eu.motionforge.app.core.movement.SquatIssue
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionNarratorTest {
    private val plan = SessionPlan(
        "Test", TrainingCategory.FITNESS,
        listOf(
            SessionStep.Work("bodyweight_squat", "Bodyweight Squat", 60, countsReps = true),
            SessionStep.Rest(15, "Glute Bridge"),
            SessionStep.Work("glute_bridge", "Glute Bridge", 40, countsReps = false),
        ),
    )
    private val tips = mapOf("glute_bridge" to listOf("Press through your heels.", "Ribs down."))

    private fun run(s: SessionState, vararg e: SessionEvent) = e.fold(s) { acc, ev -> SessionEngine.reduce(acc, ev) }

    @Test
    fun startingAnnouncesTheFirstExercise() {
        val ready = SessionState(plan)
        val started = run(ready, SessionEvent.Start(cameraUsed = true))
        val lines = SessionNarrator.onTransition(ready, started, tips, liveFeedback = true)
        assertEquals(listOf(CoachLine("Bodyweight Squat. 60 seconds. I'll count your reps and check each one.", CuePriority.ANNOUNCE)), lines)
    }

    @Test
    fun restAnnouncesWhatComesNext() {
        val s = run(SessionState(plan), SessionEvent.Start(false))
        val rest = run(s, SessionEvent.Skip)
        assertEquals("Rest. Next up: Glute Bridge.", SessionNarrator.onTransition(s, rest, tips, false).single().text)
    }

    @Test
    fun tipsAreReadOnStepsWithoutCameraFeedback() {
        var s = run(SessionState(plan), SessionEvent.Start(false), SessionEvent.Skip, SessionEvent.Skip)
        val spoken = mutableListOf<String>()
        repeat(39) {
            val next = run(s, SessionEvent.Tick(false))
            spoken += SessionNarrator.onTransition(s, next, tips, liveFeedback = false).map { it.text }
            s = next
        }
        // tip at 8 s; the 28 s tip would land too close to the end; then the ten-second warning
        assertEquals(listOf("Press through your heels.", "Ten seconds left."), spoken)
    }

    @Test
    fun noTipsWhenTheCameraIsGivingFeedback() {
        var s = run(SessionState(plan), SessionEvent.Start(true))
        val spoken = mutableListOf<CoachLine>()
        repeat(30) {
            val next = run(s, SessionEvent.Tick(true))
            spoken += SessionNarrator.onTransition(s, next, mapOf("bodyweight_squat" to listOf("Tip")), liveFeedback = true)
            s = next
        }
        assertTrue(spoken.none { it.priority == CuePriority.INFO })
    }

    @Test
    fun finishingIsAnnouncedOnce() {
        val s = run(SessionState(plan), SessionEvent.Start(false))
        val done = run(s, SessionEvent.Stop)
        assertEquals("Session ended.", SessionNarrator.onTransition(s, done, tips, false).single().text)
        assertTrue(SessionNarrator.onTransition(done, done, tips, false).isEmpty())
    }

    @Test
    fun squatLines() {
        assertEquals(CoachLine("Three. Slow down on the way down.", CuePriority.CORRECTION),
            SessionNarrator.squatLine(SquatEvent.RepCompleted(3, setOf(SquatIssue.RUSHED, SquatIssue.CHEST_DROP))))
        val clean = SessionNarrator.squatLine(SquatEvent.RepCompleted(2, emptySet()))
        assertTrue(clean.text.startsWith("Two. "))
        assertEquals(CuePriority.COUNT, clean.priority)
        assertEquals(SessionNarrator.SHALLOW, SessionNarrator.squatLine(SquatEvent.ShallowRep).text)
    }

    @Test
    fun squatCardTones() {
        assertEquals(CoachTone.PAUSED, SessionNarrator.squatCard(null, tracking = false).tone)
        assertEquals(CoachTone.NEUTRAL, SessionNarrator.squatCard(null, tracking = true).tone)
        assertEquals(CoachTone.GOOD, SessionNarrator.squatCard(SquatEvent.RepCompleted(1, emptySet()), true).tone)
        val adj = SessionNarrator.squatCard(SquatEvent.RepCompleted(1, setOf(SquatIssue.KNEES_IN)), true)
        assertEquals(CoachTone.ADJUST, adj.tone)
        assertEquals(SquatIssue.KNEES_IN.message, adj.message)
    }

    @Test
    fun onlyCleanJabsArePraised() {
        assertEquals(SessionNarrator.GOOD_JAB, SessionNarrator.jabLine(JabResult(1, true))?.text)
        assertNull(SessionNarrator.jabLine(JabResult(2, false)))
    }

    @Test
    fun aFormCueIsSpokenOnlyWhenItChanges() {
        val cue = FormFeedback.Cue(FormIssue.HANDS_LOW, 0)
        assertEquals(FormIssue.HANDS_LOW.spoken, SessionNarrator.formLine(FormFeedback.Steady(0), cue)?.text)
        assertNull(SessionNarrator.formLine(cue, cue))
        assertNull(SessionNarrator.formLine(cue, FormFeedback.Steady(0)))
    }

    @Test
    fun boxingCardCountsCleanJabs() {
        val c = SessionNarrator.boxingCard(FormFeedback.Steady(5), BoxingDrill.JAB, 4)
        assertEquals("Form check (experimental) · 5 jabs, 4 clean", c.title)
        assertEquals(CoachTone.GOOD, c.tone)
    }
}
