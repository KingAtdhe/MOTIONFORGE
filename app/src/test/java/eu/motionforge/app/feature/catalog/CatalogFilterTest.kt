package eu.motionforge.app.feature.catalog

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal
import eu.motionforge.app.data.ExerciseCatalogParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class CatalogFilterTest {

    private val catalog = ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText())

    @Test
    fun defaultFilterShowsEverythingInOrder() {
        val f = CatalogFilter()
        assertFalse(f.isActive)
        assertEquals(catalog, f.apply(catalog))
    }

    @Test
    fun categoryFilter() {
        val fighting = CatalogFilter(category = TrainingCategory.FIGHTING_FUNDAMENTALS).apply(catalog)
        assertTrue(fighting.isNotEmpty())
        assertTrue(fighting.all { it.category == TrainingCategory.FIGHTING_FUNDAMENTALS })
    }

    @Test
    fun durationFilterIsInclusive() {
        val short = CatalogFilter(duration = DurationFilter.UP_TO_45).apply(catalog)
        assertTrue(short.isNotEmpty())
        assertTrue(short.all { it.durationSeconds <= 45 })
        assertTrue(short.any { it.durationSeconds == 45 })
    }

    @Test
    fun combinedFiltersCanBeEmpty() {
        // No fitness lesson is under 45 s AND... warm-up is 120 s; ensure an impossible combo yields empty, not a crash.
        val none = CatalogFilter(TrainingCategory.FITNESS, DurationFilter.UP_TO_45).apply(catalog.filter { it.durationSeconds > 45 })
        assertTrue(none.isEmpty())
    }

    @Test
    fun equipmentFilter() {
        val none = CatalogFilter(equipment = EquipmentFilter.NONE).apply(catalog)
        val with = CatalogFilter(equipment = EquipmentFilter.WITH).apply(catalog)
        assertTrue(with.isNotEmpty() && none.isNotEmpty())
        assertTrue(with.all { it.needsEquipment } && none.none { it.needsEquipment })
        assertEquals(catalog.size, none.size + with.size)
        assertTrue(CatalogFilter(equipment = EquipmentFilter.WITH).isActive)
    }

    @Test
    fun suggestionStaysInFocus() {
        val s = LessonSuggestions.suggest(catalog, TrainingCategory.FIGHTING_FUNDAMENTALS, TrainingGoal.LEARN_BASICS, null)
        assertEquals(TrainingCategory.FIGHTING_FUNDAMENTALS, s!!.category)
        assertEquals("boxing_stance", s.id)
    }

    @Test
    fun routineGoalStartsWithWarmUp() {
        val s = LessonSuggestions.suggest(catalog, TrainingCategory.FITNESS, TrainingGoal.BUILD_ROUTINE, null)
        assertEquals(LessonSuggestions.WARM_UP_ID, s!!.id)
    }

    @Test
    fun suggestionAvoidsLastViewed() {
        val s = LessonSuggestions.suggest(catalog, TrainingCategory.FITNESS, TrainingGoal.BUILD_ROUTINE, LessonSuggestions.WARM_UP_ID)
        assertTrue(s!!.id != LessonSuggestions.WARM_UP_ID)
    }

    @Test
    fun emptyCatalogGivesNoSuggestion() {
        assertEquals(null, LessonSuggestions.suggest(emptyList(), null, null, null))
    }

    // ------------------------------------------------------------------ search
    private fun names(q: String, f: CatalogFilter = CatalogFilter()) = f.copy(query = q).apply(catalog).map { it.id }

    @Test
    fun blankSearchChangesNothing() {
        assertEquals(catalog, CatalogFilter(query = "   ").apply(catalog))
        assertFalse(CatalogFilter(query = " ").isActive)
        assertTrue(CatalogFilter(query = "jab").isActive)
    }

    @Test
    fun searchFindsByNameAnyCaseAndPlural() {
        assertEquals(names("squat"), names("SQUATS"))
        assertTrue("bodyweight_squat" in names("squat"))
        assertTrue(names("squat").all { "squat" in it })
        assertEquals("best match first", "boxing_jab", names("jab").first())
    }

    @Test
    fun searchJoinsWordsTypedApart() {
        val push = names("push up")
        assertEquals(names("pushup"), push)
        assertTrue("push_up" in push && "knee_push_up" in push)
        assertTrue(push.all { "push_up" in it })
        assertEquals(listOf("knee_push_up"), names("knee push up"))
    }

    @Test
    fun everydayWordsFindTheRightMoves() {
        assertTrue(names("abs").containsAll(listOf("forearm_plank", "dead_bug")))
        assertTrue(names("abs").none { it.startsWith("boxing_") })
        assertTrue(names("punch").containsAll(listOf("boxing_jab", "boxing_cross", "boxing_lead_hook", "boxing_rear_uppercut")))
        assertTrue(names("punch").none { it == "bodyweight_squat" })
        assertTrue(names("defence").containsAll(listOf("boxing_slip", "boxing_roll")))
        assertTrue(names("defence").none { it.contains("squat") || it.contains("push") })
        assertTrue("dumbbell_biceps_curl" in names("biceps"))
        assertTrue("kettlebell_deadlift" in names("weights"))
    }

    @Test
    fun wordStartsOnlyAndAllWordsMustMatch() {
        assertEquals("'arm' must rank Arm Circles first, not the warm-up", "arm_circles", names("arm").first())
        assertEquals(listOf("dumbbell_biceps_curl", "dumbbell_hammer_curl"), names("dumbbell curl"))
        assertTrue(names("xyzzy").isEmpty())
    }

    @Test
    fun searchCombinesWithFilters() {
        val fighting = names("jab", CatalogFilter(category = TrainingCategory.FIGHTING_FUNDAMENTALS))
        assertEquals(names("jab"), fighting)
        assertTrue(names("jab", CatalogFilter(category = TrainingCategory.FITNESS)).isEmpty())
        assertTrue(names("dumbbell", CatalogFilter(equipment = EquipmentFilter.NONE)).isEmpty())
    }

    @Test
    fun accentsAndDashesAreIgnored() {
        assertEquals(names("cat-cow"), names("cat cow"))
        assertEquals(names("squat"), names("squât"))
    }
}
