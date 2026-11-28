package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FormScoreTest {
    private fun set(id: String, reps: Int?, clean: Int?, shallow: Int? = 0) = ExerciseRecord(id, id, 60, reps, "good", null, clean, shallow)
    private fun session(at: Long, vararg e: ExerciseRecord) = SessionRecord(at, "S", TrainingCategory.FITNESS, at, 600, null, true, e.toList())

    @Test
    fun onlyMovesWithFormRules() {
        assertTrue(FormScore.hasRules("bodyweight_squat"))
        assertTrue(FormScore.hasRules("knee_push_up"))
        assertTrue(FormScore.hasRules("reverse_lunge"))
        assertFalse(FormScore.hasRules("glute_bridge"))
        assertFalse(FormScore.hasRules("jumping_jack"))
        assertFalse(FormScore.hasRules("boxing_jab"))
    }

    @Test
    fun aSetNeedsEnoughAttemptsAndCountsShallowOnes() {
        assertNull("too few", FormScore.of(set("bodyweight_squat", 3, 3, 1)))
        val t = FormScore.of(set("bodyweight_squat", 8, 6, 2))!!
        assertEquals(6, t.clean)
        assertEquals(10, t.attempts)
        assertEquals(60, t.percent)
        assertNull("not measured", FormScore.of(set("bodyweight_squat", null, null)))
        assertNull("no form rules", FormScore.of(set("glute_bridge", 12, null)))
        // clean never exceeds the counted reps (a stale or odd record)
        assertEquals(10, FormScore.of(set("push_up", 10, 14, 0))!!.clean)
    }

    @Test
    fun aSessionSumsItsSets() {
        val s = session(1, set("bodyweight_squat", 3, 3), set("push_up", 3, 2), set("glute_bridge", 10, null))
        val t = FormScore.of(s)!!
        assertEquals(FormTally(5, 6), t)
        assertEquals(83, t.percent)
        assertNull(FormScore.of(session(2, set("bodyweight_squat", 2, 2))))
    }

    @Test
    fun trendsPerExerciseNewestFirst() {
        val h = listOf(
            session(100, set("bodyweight_squat", 10, 8), set("push_up", 6, 6)),
            session(200, set("bodyweight_squat", 10, 9, 0), set("push_up", 2, 2)),     // push-ups too few: skipped
            session(300, set("bodyweight_squat", 10, 10)),
        )
        val trends = FormScore.trends(h)
        assertEquals(listOf("bodyweight_squat", "push_up"), trends.map { it.exerciseId })
        assertEquals(listOf(80, 90, 100), trends[0].recent)
        assertEquals(100, trends[0].last)
        assertEquals(listOf(100), trends[1].recent)
    }
}
