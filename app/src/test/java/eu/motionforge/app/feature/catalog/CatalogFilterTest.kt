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
}
