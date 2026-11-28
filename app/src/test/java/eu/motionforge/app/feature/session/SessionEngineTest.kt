package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.ExerciseCatalogParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SessionEngineTest {
    private val catalog = ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText())
    private val squat = catalog.first { it.id == SessionPlanner.SQUAT_ID }
    private fun SessionState.on(vararg e: SessionEvent) = e.fold(this) { s, ev -> SessionEngine.reduce(s, ev) }
    private fun SessionState.ticks(n: Int, tracking: Boolean = false) = (1..n).fold(this) { s, _ -> SessionEngine.reduce(s, SessionEvent.Tick(tracking)) }

    @Test
    fun singleLessonRunsToCompletion() {
        val s = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(false)).ticks(squat.durationSeconds)
        assertEquals(SessionPhase.FINISHED, s.phase)
        assertEquals(1, s.results.size)
        assertEquals(squat.durationSeconds, s.results[0].elapsedSeconds)
        assertEquals(TrackingQuality.NOT_USED, s.results[0].trackingQuality)
        assertNull("no camera, no rep count", s.results[0].repetitions)
        assertTrue(s.isSaveable)
        assertFalse(s.endedEarly)
    }

    @Test
    fun ticksDoNothingUntilStartedOrWhilePaused() {
        val ready = SessionState(SessionPlanner.single(squat))
        assertEquals(ready, ready.ticks(5))
        val paused = ready.on(SessionEvent.Start(false)).ticks(3).on(SessionEvent.Pause)
        assertEquals(paused, paused.ticks(10))
        assertEquals(4, paused.on(SessionEvent.Resume).ticks(1).elapsedTotal)
    }

    @Test
    fun quickSessionHasRestsBetweenExercises() {
        val plan = SessionPlanner.quick(catalog, TrainingCategory.FITNESS)!!
        assertTrue(plan.steps.first() is SessionStep.Work)
        assertEquals("standing_mobility_warmup", (plan.steps.first() as SessionStep.Work).exerciseId)
        plan.steps.zipWithNext().forEach { (a, b) -> assertTrue(a is SessionStep.Work != b is SessionStep.Work) }
        assertTrue(plan.workCount in 2..4)
        val boxing = SessionPlanner.quick(catalog, TrainingCategory.FIGHTING_FUNDAMENTALS)!!
        assertTrue(boxing.steps.filterIsInstance<SessionStep.Work>().drop(1).all { w -> catalog.first { it.id == w.exerciseId }.category == TrainingCategory.FIGHTING_FUNDAMENTALS })
    }

    @Test
    fun countedMovesCountReps() {
        catalog.forEach { e ->
            val w = SessionPlanner.single(e).steps.single() as SessionStep.Work
            assertEquals(e.id, eu.motionforge.app.core.movement.CountedMove.forExercise(e.id) != null, w.countsReps)
        }
        assertEquals(true, (SessionPlanner.single(squat).steps.single() as SessionStep.Work).countsReps)
    }

    @Test
    fun repsAreKeptOnlyWithUsableTracking() {
        val start = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(true))
        val good = start.ticks(20, tracking = true).on(SessionEvent.RepCounted, SessionEvent.RepCounted).ticks(squat.durationSeconds - 20, tracking = true)
        assertEquals(2, good.results[0].repetitions)
        assertEquals(TrackingQuality.GOOD, good.results[0].trackingQuality)
        val poor = start.on(SessionEvent.RepCounted).ticks(squat.durationSeconds, tracking = false)
        assertNull(poor.results[0].repetitions)
        assertEquals(TrackingQuality.UNAVAILABLE, poor.results[0].trackingQuality)
    }

    @Test
    fun repsIgnoredDuringRestAndForOtherExercises() {
        val plan = SessionPlanner.quick(catalog, TrainingCategory.FITNESS)!!
        val s = SessionState(plan).on(SessionEvent.Start(true), SessionEvent.RepCounted) // warm-up step
        assertEquals(0, s.stepReps)
    }

    @Test
    fun skipMovesOnAndRecordsPartialWork() {
        val plan = SessionPlanner.quick(catalog, TrainingCategory.FITNESS)!!
        val s = SessionState(plan).on(SessionEvent.Start(false)).ticks(12).on(SessionEvent.Skip)
        assertEquals(1, s.stepIndex)
        assertTrue(s.currentStep is SessionStep.Rest)
        assertEquals(12, s.results.single().elapsedSeconds)
        assertEquals(SessionPlanner.REST_SECONDS, s.remainingInStep)
    }

    @Test
    fun stopEarlyKeepsWhatWasDone() {
        val s = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(false)).ticks(25).on(SessionEvent.Stop)
        assertEquals(SessionPhase.FINISHED, s.phase)
        assertTrue(s.endedEarly)
        assertEquals(25, s.workSeconds)
        assertTrue(s.isSaveable)
    }

    @Test
    fun tinySessionsAreNotSaveable() {
        val s = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(false)).ticks(4).on(SessionEvent.Stop)
        assertFalse(s.isSaveable)
        assertFalse(SessionState(SessionPlanner.single(squat)).on(SessionEvent.Stop).isSaveable)
    }

    @Test
    fun wholeQuickSessionFinishesWithAllResults() {
        val plan = SessionPlanner.quick(catalog, TrainingCategory.FIGHTING_FUNDAMENTALS)!!
        val s = SessionState(plan).on(SessionEvent.Start(false)).ticks(plan.totalSeconds)
        assertEquals(SessionPhase.FINISHED, s.phase)
        assertEquals(plan.workCount, s.results.size)
        assertEquals(plan.totalSeconds, s.elapsedTotal)
        assertEquals((1..plan.workCount).toList(), s.results.map { it.sequence })
    }

    @Test
    fun trackingQualityBands() {
        assertEquals(TrackingQuality.GOOD, TrackingQuality.of(true, 70, 100))
        assertEquals(TrackingQuality.PARTIAL, TrackingQuality.of(true, 30, 100))
        assertEquals(TrackingQuality.UNAVAILABLE, TrackingQuality.of(true, 29, 100))
        assertEquals(TrackingQuality.NOT_USED, TrackingQuality.of(false, 100, 100))
    }

    @Test
    fun boxingStanceAndJabStepsCarryAFormCheck() {
        val stance = catalog.first { it.id == SessionPlanner.STANCE_ID }
        val jab = catalog.first { it.id == SessionPlanner.JAB_ID }
        org.junit.Assert.assertEquals(eu.motionforge.app.core.movement.BoxingDrill.STANCE, (SessionPlanner.single(stance).steps.first() as SessionStep.Work).formDrill)
        org.junit.Assert.assertEquals(eu.motionforge.app.core.movement.BoxingDrill.JAB, (SessionPlanner.single(jab).steps.first() as SessionStep.Work).formDrill)
        org.junit.Assert.assertEquals(null, (SessionPlanner.single(squat).steps.first() as SessionStep.Work).formDrill)
    }

    @Test
    fun quickSessionNeverNeedsEquipment() {
        listOf(TrainingCategory.FITNESS, TrainingCategory.FIGHTING_FUNDAMENTALS, null).forEach { focus ->
            val plan = SessionPlanner.quick(catalog, focus)!!
            val ids = plan.steps.filterIsInstance<SessionStep.Work>().map { it.exerciseId }.toSet()
            assertTrue(catalog.filter { it.id in ids }.none { it.needsEquipment })
        }
    }

    @Test
    fun holdTimeIsKeptOnlyWithTheCameraAndUsableTracking() {
        val plank = catalog.first { it.id == "forearm_plank" }
        val plan = SessionPlanner.single(plank)
        assertTrue((plan.steps.single() as SessionStep.Work).holdCheck != null)
        var s = SessionState(plan).on(SessionEvent.Start(true)).ticks(10, tracking = true)
        s = s.on(SessionEvent.HoldProgress(7), SessionEvent.HoldProgress(5))      // never decreases
        assertEquals(7, s.stepHeld)
        s = s.on(SessionEvent.HoldProgress(99))                                    // never more than the step's time
        assertEquals(11, s.stepHeld)
        s = s.on(SessionEvent.Stop)
        assertEquals(11, s.results.single().heldSeconds)
        // without the camera nothing is measured
        val off = SessionState(plan).on(SessionEvent.Start(false)).ticks(10).on(SessionEvent.HoldProgress(5), SessionEvent.Stop)
        assertNull(off.results.single().heldSeconds)
        // a counted move has no hold time
        val sq = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(true)).ticks(10, tracking = true).on(SessionEvent.HoldProgress(5), SessionEvent.Stop)
        assertNull(sq.results.single().heldSeconds)
    }

    @Test
    fun formTallyCountsFlaggedAndShallowRepsOnlyForFormRuleMoves() {
        var s = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(true)).ticks(3, tracking = true)
        s = s.on(SessionEvent.RepCounted, SessionEvent.RepCounted, SessionEvent.RepCounted)
        s = s.on(SessionEvent.RepFlagged, SessionEvent.RepCounted, SessionEvent.ShallowAttempt, SessionEvent.RepFlagged, SessionEvent.RepCounted)
        s = s.ticks(squat.durationSeconds, tracking = true)
        val r = s.results.single()
        assertEquals(5, r.repetitions)
        assertEquals(3, r.cleanReps)
        assertEquals(1, r.shallowReps)

        // a move without per-rep form rules gets no form tally, even with reps counted
        val bridge = catalog.first { it.id == "glute_bridge" }
        var b = SessionState(SessionPlanner.single(bridge)).on(SessionEvent.Start(true)).ticks(2, tracking = true)
        b = b.on(SessionEvent.RepCounted, SessionEvent.RepFlagged, SessionEvent.RepCounted).ticks(bridge.durationSeconds, tracking = true)
        assertNull(b.results.single().cleanReps)
        assertNull(b.results.single().shallowReps)

        // without the camera nothing is counted, so there is no tally either
        val off = SessionState(SessionPlanner.single(squat)).on(SessionEvent.Start(false), SessionEvent.RepFlagged, SessionEvent.ShallowAttempt)
            .ticks(squat.durationSeconds)
        assertNull(off.results.single().cleanReps)
    }
}
