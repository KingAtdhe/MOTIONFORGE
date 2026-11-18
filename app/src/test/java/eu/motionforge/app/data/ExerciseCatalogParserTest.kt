package eu.motionforge.app.data

import eu.motionforge.app.core.model.AnalysisMode
import eu.motionforge.app.core.model.TrainingCategory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class ExerciseCatalogParserTest {

    /** Unit tests run with the module directory as working directory. */
    private val bundled = File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText()

    @Test
    fun bundledCatalogParses() {
        val exercises = ExerciseCatalogParser.parse(bundled)
        assertEquals(5, exercises.size)
        assertTrue(exercises.any { it.category == TrainingCategory.FITNESS })
        assertTrue(exercises.any { it.category == TrainingCategory.FIGHTING_FUNDAMENTALS })
    }

    @Test
    fun everyExerciseHasSafetyAndLimitations() {
        ExerciseCatalogParser.parse(bundled).forEach {
            assertTrue("${it.id} safety", it.safety.isNotBlank())
            assertTrue("${it.id} limitations", it.limitations.isNotBlank())
            assertTrue("${it.id} instructions", it.instructions.isNotEmpty())
        }
    }

    @Test
    fun unvalidatedMovementsDoNotAllowLiveCues() {
        val byId = ExerciseCatalogParser.parse(bundled).associateBy { it.id }
        assertEquals(AnalysisMode.DEMO_GUIDED_INITIALLY, byId.getValue("push_up").analysisMode)
        assertFalse(byId.getValue("push_up").analysisMode.allowsLiveCues)
        assertFalse(byId.getValue("boxing_cross").analysisMode.allowsLiveCues)
    }

    @Test
    fun demoAnimationsUseManifestClipNames() {
        val manifestClips = setOf(
            "idle_neutral", "squat_down", "squat_up", "pushup_down", "pushup_up", "boxing_stance",
            "boxing_jab", "boxing_cross", "boxing_guard_return", "footwork_forward", "footwork_backward",
        )
        ExerciseCatalogParser.parse(bundled).forEach {
            assertTrue("${it.id} uses unknown clip ${it.demoAnimation}", it.demoAnimation in manifestClips)
        }
    }

    @Test(expected = CatalogException::class)
    fun unknownAnalysisModeFailsLoudly() {
        ExerciseCatalogParser.parse(bundled.replaceFirst("\"limited_rule_based\"", "\"full_ai_scoring\""))
    }

    @Test(expected = CatalogException::class)
    fun duplicateIdsAreRejected() {
        val one = bundled.trim().removePrefix("[").removeSuffix("]").substringBefore("\n  },") + "\n  }"
        ExerciseCatalogParser.parse("[$one,$one]")
    }

    @Test(expected = CatalogException::class)
    fun missingSafetyIsRejected() {
        ExerciseCatalogParser.parse(bundled.replaceFirst(Regex("\"safety\": \"[^\"]*\""), "\"safety\": \"\""))
    }
}
