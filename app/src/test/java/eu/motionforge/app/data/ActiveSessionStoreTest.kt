package eu.motionforge.app.data

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.feature.session.SessionEngine
import eu.motionforge.app.feature.session.SessionEvent
import eu.motionforge.app.feature.session.SessionPhase
import eu.motionforge.app.feature.session.SessionPlan
import eu.motionforge.app.feature.session.SessionSnapshot
import eu.motionforge.app.feature.session.SessionState
import eu.motionforge.app.feature.session.SessionStep
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

/**
 * A workout must survive Android killing the app: the store is written by one process and read back by a fresh one
 * (simulated with a new store instance over the same app storage, as a restarted process would create).
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class ActiveSessionStoreTest {
    private val context = RuntimeEnvironment.getApplication()
    private val plan = SessionPlan(
        "Quick fitness", TrainingCategory.FITNESS,
        listOf(
            SessionStep.Work("bodyweight_squat", "Squat", 30, countsReps = true),
            SessionStep.Rest(15, "Push-up"),
            SessionStep.Work("push_up", "Push-up", 30, countsReps = true),
        ),
    )

    private fun midway(): SessionState {
        var s = SessionEngine.reduce(SessionState(plan), SessionEvent.Start(cameraUsed = true))
        repeat(12) { s = SessionEngine.reduce(s, SessionEvent.Tick(tracking = true)) }
        repeat(3) { s = SessionEngine.reduce(s, SessionEvent.RepCounted) }
        return s
    }

    @Test
    fun aWorkoutComesBackInANewProcess() {
        val now = System.currentTimeMillis()
        val before = ActiveSessionStore(context)
        val state = midway()
        before.write(SessionSnapshot("quick-fitness", state, now - 20_000, now), before.epoch)

        val after = ActiveSessionStore(context) // the app was killed and started again
        val snap = after.read(now + 5_000)!!
        assertEquals("quick-fitness", snap.planKey)
        assertEquals(state.stepIndex, snap.state.stepIndex)
        assertEquals(state.remainingInStep, snap.state.remainingInStep)
        assertEquals(3, snap.state.stepReps)
        // it continues paused, never running unattended
        assertEquals(SessionPhase.PAUSED, snap.restoredState().phase)
        after.clear()
    }

    @Test
    fun aSavedOrDiscardedWorkoutDoesNotComeBack() {
        val now = System.currentTimeMillis()
        val store = ActiveSessionStore(context)
        val staleEpoch = store.epoch
        store.clear()
        store.write(SessionSnapshot("quick-fitness", midway(), now, now), staleEpoch) // a late background write
        assertNull(ActiveSessionStore(context).read(now))
    }

    @Test
    fun anOldWorkoutIsNotOffered() {
        val now = System.currentTimeMillis()
        val store = ActiveSessionStore(context)
        store.write(SessionSnapshot("quick-fitness", midway(), now, now), store.epoch)
        assertNull(ActiveSessionStore(context).read(now + SessionSnapshot.MAX_AGE_MILLIS + 60_000))
    }
}
