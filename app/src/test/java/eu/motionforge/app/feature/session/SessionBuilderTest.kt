package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.ExerciseCatalogParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SessionBuilderTest {
    private val catalog = ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText())
    private val byId = catalog.associateBy { it.id }

    private fun build(f: SessionFocus, min: Int, db: Boolean = false, day: Long = 20_000) =
        SessionBuilder.build(catalog, SessionBuilder.Params(f, min, db, day))!!

    @Test
    fun everyFocusAndLengthBuildsAPlanCloseToItsLength() {
        for (f in SessionFocus.entries) for (m in SessionBuilder.MINUTES) {
            val p = build(f, m)
            val works = p.steps.filterIsInstance<SessionStep.Work>()
            assertTrue("$f $m: ${works.size} moves", works.size >= 2)
            assertTrue("$f $m lasts ${p.totalSeconds}", p.totalSeconds in (m * 60 - 120)..(m * 60 + 60))
            assertTrue("$f $m starts with a move", p.steps.first() is SessionStep.Work)
            assertEquals("no move twice", works.size, works.map { it.exerciseId }.toSet().size)
            works.forEach { assertNotNull(it.exerciseId, byId[it.exerciseId]) }
        }
    }

    @Test
    fun equipmentOnlyWhenAskedFor() {
        for (f in SessionFocus.entries) for (m in SessionBuilder.MINUTES) {
            build(f, m).steps.filterIsInstance<SessionStep.Work>().forEach { assertTrue(it.exerciseId, !byId.getValue(it.exerciseId).needsEquipment) }
        }
        val upper = build(SessionFocus.UPPER, 20, db = true).steps.filterIsInstance<SessionStep.Work>()
        assertTrue("dumbbell moves appear", upper.any { byId.getValue(it.exerciseId).needsEquipment })
        upper.forEach { w -> byId.getValue(w.exerciseId).equipment.filter { "(" !in it }.forEach { assertTrue(it, it.startsWith("Dumbbell")) } }
    }

    @Test
    fun warmUpFirstAndCoolDownLast() {
        val p = build(SessionFocus.LEGS, 15).steps.filterIsInstance<SessionStep.Work>()
        assertEquals("standing_mobility_warmup", p.first().exerciseId)
        assertTrue(p.last().exerciseId.contains("stretch") || p.last().exerciseId == "childs_pose")
        val stretch = build(SessionFocus.STRETCH, 10).steps.filterIsInstance<SessionStep.Work>()
        assertTrue("no warm-up before stretching", stretch.none { it.exerciseId == "standing_mobility_warmup" })
    }

    @Test
    fun boxingStartsWithTheStanceAndNeverScoresFootwork() {
        val p = build(SessionFocus.BOXING, 10)
        assertEquals(TrainingCategory.FIGHTING_FUNDAMENTALS, p.type)
        val works = p.steps.filterIsInstance<SessionStep.Work>()
        assertEquals(SessionPlanner.STANCE_ID, works[1].exerciseId)
        assertTrue(works.none { it.exerciseId.startsWith("footwork_") })
    }

    @Test
    fun theSameDayGivesTheSameSessionAndAnotherDayAnother() {
        assertEquals(build(SessionFocus.CORE, 10, day = 5), build(SessionFocus.CORE, 10, day = 5))
        assertNotEquals(build(SessionFocus.CORE, 10, day = 5), build(SessionFocus.CORE, 10, day = 6))
    }

    @Test
    fun keysRoundTrip() {
        val k = SessionBuilder.key(SessionFocus.UPPER, 15, true, 20_123)
        assertEquals(SessionBuilder.Params(SessionFocus.UPPER, 15, true, 20_123), SessionBuilder.parseKey(k))
        assertNull(SessionBuilder.parseKey("build-upper-7-d-1"))
        assertNull(SessionBuilder.parseKey("quick"))
        assertNull(SessionBuilder.parseKey("build-nope-10-n-1"))
    }
}
