package eu.motionforge.app.feature.session

import eu.motionforge.app.data.ExerciseCatalogParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class FlowsTest {
    private val catalog = ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText())
    private val byId = catalog.associateBy { it.id }

    @Test
    fun everyFlowUsesOnlyCatalogueMovesWithoutEquipment() {
        for (f in Flow.entries) {
            f.moves.forEach { (id, s) ->
                val e = byId[id]
                assertTrue("${f.name}: $id missing", e != null)
                assertTrue("${f.name}: $id needs equipment", !e!!.needsEquipment)
                assertTrue("${f.name}: $id $s s", s in 30..90)
            }
        }
    }

    @Test
    fun flowsBuildWithShortTransitionsAndKeepTheLessonsCameraChecks() {
        for (f in Flow.entries) {
            val p = Flows.build(f, catalog)!!
            val works = p.steps.filterIsInstance<SessionStep.Work>()
            assertEquals(f.moves.size, works.size)
            assertEquals(f.moves.map { it.first }, works.map { it.exerciseId })
            // a transition between every two moves, none at the start or the end
            assertTrue(p.steps.first() is SessionStep.Work && p.steps.last() is SessionStep.Work)
            p.steps.filterIsInstance<SessionStep.Rest>().forEach { assertEquals(Flows.TRANSITION_SECONDS, it.durationSeconds) }
            assertEquals(works.size - 1, p.steps.count { it is SessionStep.Rest })
            assertTrue("${f.name}: ${Flows.minutes(f)} min", Flows.minutes(f) in 4..10)
            // no boxing form drills in a mobility flow
            assertTrue(works.all { it.formDrill == null })
        }
    }

    @Test
    fun keysRoundTripAndNeverCollideWithOtherSessionKeys() {
        for (f in Flow.entries) {
            assertEquals(f, Flows.parseKey(Flows.key(f)))
            assertNull(SessionBuilder.parseKey(Flows.key(f)))
        }
        assertNull(Flows.parseKey("flow-nope"))
        assertNull(Flows.parseKey("build-core-10-n-20100"))
        assertNull(Flows.parseKey("lesson-flow-morning"))
    }
}
