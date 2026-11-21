package eu.motionforge.app.data

import eu.motionforge.app.core.model.AnalysisMode
import eu.motionforge.app.core.model.ReviewStatus
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
        assertEquals(17, exercises.size)
        assertTrue(exercises.any { it.category == TrainingCategory.FITNESS })
        assertTrue(exercises.any { it.category == TrainingCategory.FIGHTING_FUNDAMENTALS })
    }

    @Test
    fun everyExerciseHasSafetyAndLimitations() {
        ExerciseCatalogParser.parse(bundled).forEach {
            assertTrue("${it.id} safety", it.safety.isNotBlank())
            assertTrue("${it.id} limitations", it.limitations.isNotBlank())
            assertTrue("${it.id} instructions", it.instructions.isNotEmpty())
            assertTrue("${it.id} purpose", it.purpose.isNotBlank())
            assertTrue("${it.id} space", it.space.isNotBlank())
            assertTrue("${it.id} common mistakes", it.commonMistakes.isNotEmpty())
        }
    }

    @Test
    fun mvpMovementSetIsPresent() {
        val ids = ExerciseCatalogParser.parse(bundled).map { it.id }.toSet()
        listOf(
            "bodyweight_squat", "hip_hinge", "push_up", "boxing_stance", "boxing_jab", "boxing_cross",
            "boxing_guard_return", "footwork_forward_backward",
        ).forEach { assertTrue("missing $it", it in ids) }
    }

    @Test
    fun allDraftContentIsMarkedAsDraft() {
        // Until a qualified coach signs off, nothing may claim to be reviewed.
        ExerciseCatalogParser.parse(bundled).forEach {
            assertEquals(it.id, ReviewStatus.DRAFT_PENDING_COACH_REVIEW, it.reviewStatus)
        }
    }

    @Test
    fun hipHingeAndFootworkNeverAllowLiveCues() {
        val byId = ExerciseCatalogParser.parse(bundled).associateBy { it.id }
        assertFalse(byId.getValue("hip_hinge").analysisMode.allowsLiveCues)
        assertFalse(byId.getValue("footwork_forward_backward").analysisMode.allowsLiveCues)
        assertFalse(byId.getValue("standing_mobility_warmup").analysisMode.allowsLiveCues)
    }

    @Test
    fun noForbiddenClaimsInContent() {
        val forbidden = listOf("prevent injury", "prevents injury", "perfect", "medically", "diagnos", "guarantee", "knockout", "power punch")
        val lower = bundled.lowercase()
        forbidden.forEach { assertFalse("content contains '$it'", it in lower) }
    }

    @Test
    fun dataCopyMatchesBundledAsset() {
        // data/exercises.json (spec package) and the app asset must not drift apart.
        assertEquals(File("../data/exercises.json").readText(), bundled)
    }

    @Test(expected = CatalogException::class)
    fun missingDemoAnimationKeyIsRejected() {
        ExerciseCatalogParser.parse(bundled.replaceFirst(Regex("\"demoAnimation\": [^,]*,"), ""))
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
            "idle_neutral", "warmup_march", "hip_hinge_down", "hip_hinge_up", "squat_down", "squat_up", "pushup_down", "pushup_up", "boxing_stance",
            "boxing_jab", "boxing_cross", "boxing_guard_return", "footwork_forward", "footwork_backward",
            "boxing_lead_hook", "boxing_slip", "footwork_lateral", "reverse_lunge", "calf_raise", "step_jack", "glute_bridge", "plank_hold",
        )
        ExerciseCatalogParser.parse(bundled).forEach {
            val clip = it.demoAnimation ?: return@forEach
            assertTrue("${it.id} uses unknown clip $clip", clip in manifestClips)
        }
    }

    @Test
    fun addedLessonsGiveNoAutomatedFormFeedback() {
        // lessons added after the MVP set have no validated camera rule yet
        val byId = ExerciseCatalogParser.parse(bundled).associateBy { it.id }
        listOf("reverse_lunge", "glute_bridge", "forearm_plank", "step_jack", "calf_raise", "boxing_lead_hook", "boxing_slip", "footwork_lateral")
            .forEach { assertFalse(it, byId.getValue(it).analysisMode.allowsLiveCues) }
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
