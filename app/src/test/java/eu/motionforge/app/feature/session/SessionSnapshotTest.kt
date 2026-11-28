package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.BoxingDrill
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionSnapshotTest {
    private val plan = SessionPlan(
        "Quick boxing", TrainingCategory.FIGHTING_FUNDAMENTALS,
        listOf(
            SessionStep.Work("boxing_stance", "Boxing stance", 40, countsReps = false, formDrill = BoxingDrill.STANCE),
            SessionStep.Rest(15, "Jab"),
            SessionStep.Work("bodyweight_squat", "Squat", 30, countsReps = true),
            SessionStep.Rest(15, "Plank"),
            SessionStep.Work("forearm_plank", "Plank", 30, countsReps = false, holdCheck = eu.motionforge.app.core.movement.HoldCheck.PLANK),
            SessionStep.Rest(45, "Round 1"),
            SessionStep.Work("boxing_stance_bounce", "Round 1", 90, countsReps = false, formDrill = BoxingDrill.STANCE,
                round = 1, calls = listOf("Jab", "One, two"), callEverySeconds = 6),
        ),
    )

    private fun midway(): SessionState {
        var s = SessionEngine.reduce(SessionState(plan), SessionEvent.Start(cameraUsed = true))
        repeat(45) { s = SessionEngine.reduce(s, SessionEvent.Tick(tracking = it % 2 == 0)) }
        return s
    }

    @Test
    fun roundTripKeepsEverything() {
        val s = midway()
        val snap = SessionSnapshot("quick", s, 1_000L, 2_000L)
        val back = SessionSnapshot.decode(SessionSnapshot.encode(snap))
        assertEquals(snap, back)
    }

    @Test
    fun runningSessionComesBackPaused() {
        val snap = SessionSnapshot("quick", midway(), 0, 0)
        assertEquals(SessionPhase.RUNNING, snap.state.phase)
        val r = snap.restoredState()
        assertEquals(SessionPhase.PAUSED, r.phase)
        assertEquals(snap.state.results, r.results)
        assertEquals(snap.state.remainingInStep, r.remainingInStep)
    }

    @Test
    fun finishedUnsavedStaysFinished() {
        val s = SessionEngine.reduce(midway(), SessionEvent.Stop)
        assertEquals(SessionPhase.FINISHED, SessionSnapshot("quick", s, 0, 0).restoredState().phase)
    }

    @Test
    fun rejectsGarbageAndTampering() {
        assertNull(SessionSnapshot.decode("not json"))
        assertNull(SessionSnapshot.decode("{}"))
        val good = SessionSnapshot.encode(SessionSnapshot("quick", midway(), 0, 0))
        assertNull(SessionSnapshot.decode(good.replace("\"stepIndex\":1", "\"stepIndex\":9")))
        assertNull(SessionSnapshot.decode(good.replace("\"version\":1", "\"version\":99")))
    }

    @Test
    fun expiresAfterADay() {
        val snap = SessionSnapshot("quick", midway(), 0, 1_000_000L)
        assertFalse(snap.isExpired(1_000_000L + 60_000))
        assertTrue(snap.isExpired(1_000_000L + SessionSnapshot.MAX_AGE_MILLIS + 1))
    }

    @Test
    fun roundTripKeepsFormTallies() {
        var s = SessionEngine.reduce(SessionState(plan), SessionEvent.Start(cameraUsed = true))
        repeat(56) { s = SessionEngine.reduce(s, SessionEvent.Tick(tracking = true)) }      // into the squat
        s = listOf(SessionEvent.RepFlagged, SessionEvent.RepCounted, SessionEvent.ShallowAttempt, SessionEvent.RepCounted)
            .fold(s) { a, e -> SessionEngine.reduce(a, e) }
        assertEquals(1, s.stepFlagged)
        assertEquals(1, s.stepShallow)
        val snap = SessionSnapshot("quick", s, 1_000L, 2_000L)
        assertEquals(snap, SessionSnapshot.decode(SessionSnapshot.encode(snap)))
        repeat(40) { s = SessionEngine.reduce(s, SessionEvent.Tick(tracking = true)) }      // the squat closes
        val closed = SessionSnapshot("quick", s, 1_000L, 2_000L)
        val back = SessionSnapshot.decode(SessionSnapshot.encode(closed))!!
        val squat = back.state.results.first { it.exerciseId == "bodyweight_squat" }
        assertEquals(1, squat.cleanReps)
        assertEquals(1, squat.shallowReps)
    }
}
