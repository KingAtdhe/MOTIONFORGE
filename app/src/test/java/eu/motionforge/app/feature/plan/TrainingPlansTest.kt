package eu.motionforge.app.feature.plan

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.ExerciseCatalogParser
import eu.motionforge.app.feature.progress.ExerciseRecord
import eu.motionforge.app.feature.progress.ProgressStats
import eu.motionforge.app.feature.progress.SessionRecord
import eu.motionforge.app.feature.session.SessionEngine
import eu.motionforge.app.feature.session.SessionEvent
import eu.motionforge.app.feature.session.SessionPhase
import eu.motionforge.app.feature.session.SessionSnapshot
import eu.motionforge.app.feature.session.SessionState
import eu.motionforge.app.feature.session.SessionStep
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class TrainingPlansTest {
    private val catalog = ExerciseCatalogParser.parse(File("src/main/assets/exercise_data/exercises.json").readText())

    private fun session(at: Long, vararg sets: Pair<String, Int?>) = SessionRecord(
        at, "s", TrainingCategory.FITNESS, at, 60, null, true,
        sets.map { (id, reps) -> ExerciseRecord(id, id, 30, reps, "good") },
    )

    @Test
    fun everyPlanExerciseExistsAndEveryRepTargetHasACounter() {
        val ids = catalog.map { it.id }.toSet()
        TrainingPlans.ALL.forEach { plan ->
            plan.days.flatMap { it.items }.forEach { item ->
                assertTrue("${plan.id}: ${item.exerciseId}", item.exerciseId in ids)
                if (item.reps != null) {
                    assertEquals(plan.weeks, item.reps.size)
                    assertNotNull("${item.exerciseId} has a rep target but no counter",
                        eu.motionforge.app.core.movement.CountedMove.forExercise(item.exerciseId))
                }
            }
            (0 until plan.totalSessions).forEach { i -> assertNotNull(PlanSessions.build(plan, i, catalog, emptyList())) }
        }
        assertFalse(TrainingPlans.FOUNDATIONS.needsEquipment)
        assertFalse(TrainingPlans.BOXING_BASICS.needsEquipment)
    }

    @Test
    fun keysRoundTripAndRejectNonsense() {
        val p = TrainingPlans.BOXING_BASICS
        assertEquals(p to 7, TrainingPlans.parseKey(TrainingPlans.key(p, 7)))
        assertNull(TrainingPlans.parseKey("plan-boxing-basics-99"))
        assertNull(TrainingPlans.parseKey("plan-nope-1"))
        assertNull(TrainingPlans.parseKey("quick"))
    }

    @Test
    fun targetsStartAtThePlanAndFollowTheLastCountedSet() {
        val squat = TrainingPlans.FOUNDATIONS.days[0].items.first { it.exerciseId == "bodyweight_squat" }
        assertEquals(8, PlanProgression.target(squat, 0, emptyList()))
        assertEquals(10, PlanProgression.target(squat, 1, emptyList()))
        // did 9 last time: aim for 10
        assertEquals(10, PlanProgression.target(squat, 0, listOf(session(1, "bodyweight_squat" to 9))))
        // a poor day never drops below the plan
        assertEquals(10, PlanProgression.target(squat, 1, listOf(session(1, "bodyweight_squat" to 4))))
        // a huge day is capped
        assertEquals(8 + PlanProgression.MAX_ABOVE_PLAN, PlanProgression.target(squat, 0, listOf(session(1, "bodyweight_squat" to 40))))
        // only the latest counted set matters; uncounted sets (no camera) are ignored
        val h = listOf(session(1, "bodyweight_squat" to 12), session(2, "bodyweight_squat" to 9), session(3, "bodyweight_squat" to null))
        assertEquals(10, PlanProgression.target(squat, 0, h))
        // timed items have no target
        val warmUp = TrainingPlans.FOUNDATIONS.days[0].items.first()
        assertNull(PlanProgression.target(warmUp, 0, h))
    }

    @Test
    fun weeksAndDaysAdvanceThroughThePlan() {
        val p = TrainingPlans.FOUNDATIONS
        assertEquals(0, p.weekOf(2)); assertEquals(1, p.weekOf(3)); assertEquals(3, p.weekOf(11))
        assertEquals("A", p.dayOf(0).label); assertEquals("B", p.dayOf(1).label); assertEquals("A", p.dayOf(2).label)
        val s = PlanSessions.build(p, 3, catalog, emptyList())!!   // week 2, day B (days alternate A, B, A, B…)
        assertTrue(s.title, s.title.contains("week 2"))
        val squat = s.steps.filterIsInstance<SessionStep.Work>().first { it.exerciseId == "sumo_squat" }
        assertEquals(10, squat.targetReps)
        assertTrue(squat.durationSeconds >= 10 * 4)
    }

    @Test
    fun reachingTheTargetEndsTheSet() {
        val plan = PlanSessions.build(TrainingPlans.FOUNDATIONS, 0, catalog, emptyList())!!
        var s = SessionEngine.reduce(SessionState(plan), SessionEvent.Start(cameraUsed = true))
        s = SessionEngine.reduce(s, SessionEvent.Skip) // warm-up
        s = SessionEngine.reduce(s, SessionEvent.Skip) // rest
        val squat = s.currentStep as SessionStep.Work
        assertEquals("bodyweight_squat", squat.exerciseId)
        repeat(3) { s = SessionEngine.reduce(s, SessionEvent.Tick(tracking = true)) }
        repeat(squat.targetReps!! - 1) { s = SessionEngine.reduce(s, SessionEvent.RepCounted) }
        assertEquals("bodyweight_squat", (s.currentStep as SessionStep.Work).exerciseId)
        s = SessionEngine.reduce(s, SessionEvent.RepCounted)
        assertTrue("moved on after the target", s.currentStep is SessionStep.Rest)
        val r = s.results.last()
        assertEquals(squat.targetReps, r.repetitions)
        assertEquals(squat.targetReps, r.targetReps)
        assertEquals(SessionPhase.RUNNING, s.phase)
        // the target survives the app being closed
        val back = SessionSnapshot.decode(SessionSnapshot.encode(SessionSnapshot("plan-foundations-0", s, 0, 0)))!!
        assertEquals(squat.targetReps, back.state.results.last().targetReps)
        assertEquals(s.plan, back.state.plan)
    }

    @Test
    fun repTrendsKeepTheLatestSetsAndSpotANewBest() {
        val h = listOf(
            session(1, "bodyweight_squat" to 8, "knee_push_up" to 6),
            session(2, "bodyweight_squat" to 10),
            session(3, "bodyweight_squat" to 12, "knee_push_up" to null),
        )
        val t = ProgressStats.repTrends(h)
        assertEquals(listOf("bodyweight_squat", "knee_push_up"), t.map { it.exerciseId })
        val squat = t.first()
        assertEquals(listOf(8, 10, 12), squat.recent)
        assertEquals(12, squat.best)
        assertTrue(squat.newBest)
        assertFalse(t[1].newBest) // a single set is not a "new best"
        val more = ProgressStats.repTrends((1..12).map { session(it.toLong(), "bodyweight_squat" to it) })
        assertEquals(ProgressStats.RECENT, more.first().recent.size)
    }
}
