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
        assertEquals(118, exercises.size)
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
        // the plank got its hold check once it was checked on rendered videos (2026-11-25); footwork never does
        assertTrue(byId.getValue("forearm_plank").analysisMode.allowsLiveCues)
        assertFalse(byId.getValue("footwork_lateral").analysisMode.allowsLiveCues)
    }

    @Test
    fun demoAnimationsUseManifestClipNames() {
        val manifestClips = setOf(
            "idle_neutral", "warmup_march", "hip_hinge_down", "hip_hinge_up", "squat_down", "squat_up", "pushup_down", "pushup_up", "boxing_stance",
            "boxing_jab", "boxing_cross", "boxing_guard_return", "footwork_forward", "footwork_backward",
            "boxing_lead_hook", "boxing_slip", "footwork_lateral", "reverse_lunge", "calf_raise", "step_jack", "glute_bridge", "plank_hold",
        "arm_circles", "band_pull_apart", "bird_dog", "boxing_lead_uppercut", "boxing_rear_hook",
        "boxing_rear_uppercut", "boxing_roll", "cat_cow", "db_bent_over_row", "db_curl", "db_lateral_raise",
        "db_rdl_down", "db_rdl_up", "db_shoulder_press", "dead_bug", "footwork_pivot", "high_knee_march",
        "incline_pushup_down", "incline_pushup_up", "kb_deadlift_down", "kb_deadlift_up", "knee_pushup_down",
        "knee_pushup_up", "mountain_climber_slow", "side_lunge", "split_squat", "sumo_squat_down", "sumo_squat_up",
        "superman",
        "forward_lunge", "db_hammer_curl", "db_front_raise", "boxing_one_two", "boxing_one_two_hook",
        "knee_crunch", "db_reverse_fly", "db_overhead_triceps", "boxing_jab_jab_cross",
        "db_squat", "db_reverse_lunge", "oblique_crunch", "boxing_double_jab",
        "boxing_body_jab", "boxing_cross_hook", "boxing_pull_back", "boxing_step_jab",
        // batch 7 (2026-11-24)
        "boxing_body_cross", "boxing_body_hook", "boxing_rear_body_hook", "boxing_jab_body_cross", "boxing_body_head_jab",
        "boxing_parry", "boxing_catch", "boxing_high_block", "boxing_body_block", "boxing_duck",
        "boxing_block_cross", "boxing_jab_slip", "boxing_slip_cross", "boxing_roll_hook", "boxing_pull_counter",
        "boxing_jab_uppercut", "boxing_uppercut_hook", "boxing_hook_cross", "boxing_cross_hook_cross", "boxing_one_two_uppercut",
        "boxing_uppercuts", "boxing_stance_bounce", "boxing_fist_rolls", "footwork_circle_left", "footwork_circle_right",
        "footwork_angle_step", "footwork_shuffle", "boxing_back_jab", "boxing_lateral_jab", "boxing_jab_pivot",
        "good_morning", "curtsy_lunge", "squat_calf_raise", "single_leg_balance", "single_leg_rdl",
        "side_leg_raise", "glute_kickback", "butt_kicks", "torso_twist", "side_bend",
        "skater_step", "wall_pushup", "wall_sit", "db_goblet_squat", "db_floor_press",
        "db_shrug", "db_calf_raise", "kb_swing", "bench_dip", "crunch",
        "heel_taps", "reverse_crunch", "toe_taps", "high_plank", "shoulder_taps",
        "single_leg_bridge", "donkey_kick", "fire_hydrant", "childs_pose", "bear_hold",
        "quad_stretch", "shoulder_stretch", "triceps_stretch", "chest_opener", "hip_flexor_stretch",
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
        val mvp = setOf(
            "standing_mobility_warmup", "bodyweight_squat", "hip_hinge", "push_up", "boxing_stance", "boxing_jab", "boxing_cross",
            "boxing_guard_return", "footwork_forward_backward",
        )
        // only lessons with a camera rule (a rep counter, hold check or guard check, each checked on rendered videos,
        // or the MVP set) may show cues, and every checked lesson says so
        byId.values.filter { it.id !in mvp }.forEach {
            assertEquals(it.id, eu.motionforge.app.core.movement.LiveChecks.has(it.id), it.analysisMode.allowsLiveCues)
        }
        // footwork is a guided drill, never scored (spec), and the bodyweight hinge stays instructional
        byId.values.filter { it.id.startsWith("footwork_") || it.id == "hip_hinge" || it.id == "standing_mobility_warmup" }.forEach {
            assertFalse(it.id, eu.motionforge.app.core.movement.LiveChecks.has(it.id))
        }
    }

    @Test
    fun equipmentLessonsSayWhatTheyNeed() {
        val byId = ExerciseCatalogParser.parse(bundled).associateBy { it.id }
        val needs = byId.values.filter { it.needsEquipment }.map { it.id }.toSet()
        assertEquals(
            setOf(
                "dumbbell_biceps_curl", "dumbbell_shoulder_press", "dumbbell_lateral_raise", "dumbbell_bent_over_row",
                "dumbbell_romanian_deadlift", "kettlebell_deadlift", "band_pull_apart", "incline_push_up",
                "dumbbell_hammer_curl", "dumbbell_front_raise", "dumbbell_reverse_fly", "dumbbell_overhead_triceps_extension",
                "dumbbell_squat", "dumbbell_reverse_lunge",
                "dumbbell_goblet_squat", "dumbbell_floor_press", "dumbbell_shrug", "dumbbell_calf_raise", "kettlebell_swing", "bench_dip",
            ),
            needs,
        )
        // optional / recommended items never make a lesson an "equipment" lesson
        assertFalse(byId.getValue("push_up").needsEquipment)
        assertFalse(byId.getValue("footwork_forward_backward").needsEquipment)
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
