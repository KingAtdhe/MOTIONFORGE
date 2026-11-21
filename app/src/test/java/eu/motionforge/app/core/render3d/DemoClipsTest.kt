package eu.motionforge.app.core.render3d

import eu.motionforge.app.core.model.ReviewStatus
import eu.motionforge.app.data.ExerciseCatalogParser
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class DemoClipsTest {

    private val assets = File("src/main/assets")

    /** The clips every coach model must provide (the build exports exactly these). */
    private val requiredClips = setOf(
        "idle_neutral", "warmup_march", "squat_down", "squat_up", "hip_hinge_down", "hip_hinge_up",
        "pushup_down", "pushup_up", "boxing_stance", "boxing_jab", "boxing_cross", "boxing_guard_return",
        "footwork_forward", "footwork_backward",
        "boxing_lead_hook", "boxing_slip", "footwork_lateral", "reverse_lunge", "calf_raise", "step_jack", "glute_bridge", "plank_hold",
        "arm_circles", "band_pull_apart", "bird_dog", "boxing_lead_uppercut", "boxing_rear_hook",
        "boxing_rear_uppercut", "boxing_roll", "cat_cow", "db_bent_over_row", "db_curl", "db_lateral_raise",
        "db_rdl_down", "db_rdl_up", "db_shoulder_press", "dead_bug", "footwork_pivot", "high_knee_march",
        "incline_pushup_down", "incline_pushup_up", "kb_deadlift_down", "kb_deadlift_up", "knee_pushup_down",
        "knee_pushup_up", "mountain_climber_slow", "side_lunge", "split_squat", "sumo_squat_down", "sumo_squat_up",
        "superman",
    )

    /** Coaches whose model is bundled. None while new coach models are being made; the app then shows written steps. */
    private val bundled = eu.motionforge.app.core.model.Coach.entries.filter { File(assets, it.manifestPath).isFile }

    /** Reads animation names straight from the GLB's JSON chunk. */
    private fun glbAnimationNames(file: File): Set<String> {
        val bytes = file.readBytes()
        val buf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals("glTF magic", 0x46546C67, buf.getInt(0))
        val jsonLength = buf.getInt(12)
        assertEquals("JSON chunk type", 0x4E4F534A, buf.getInt(16))
        val json = String(bytes, 20, jsonLength, Charsets.UTF_8)
        return Json.parseToJsonElement(json).jsonObject["animations"]!!.jsonArray
            .map { it.jsonObject["name"]!!.jsonPrimitive.content }.toSet()
    }

    @Test
    fun manifestMatchesTheExportedGlb() {
        bundled.forEach { coach ->
            val m = ClipManifest.parse(File(assets, coach.manifestPath).readText())
            val glb = File(assets, m.assetPath)
            assertTrue("GLB missing for $coach: $glb", glb.exists())
            assertEquals("clips of $coach", m.names, glbAnimationNames(glb))
        }
    }

    @Test
    fun everyCoachHasTheSameClips() {
        bundled.forEach { assertEquals(requiredClips, ClipManifest.parse(File(assets, it.manifestPath).readText()).names) }
    }

    @Test
    fun allClipsAreMarkedDraftUntilCoachReview() {
        bundled.forEach { coach ->
            ClipManifest.parse(File(assets, coach.manifestPath).readText()).clips
                .forEach { assertEquals(it.name, ReviewStatus.DRAFT_PENDING_COACH_REVIEW, it.reviewStatus) }
        }
    }

    @Test
    fun everyLessonEitherHasItsClipOrIsKnownToBePending() {
        val pending = emptySet<String>()
        val catalog = ExerciseCatalogParser.parse(File(assets, ExerciseCatalogParser.ASSET_PATH).readText())
        catalog.mapNotNull { it.demoAnimation }.forEach { clip ->
            assertTrue("clip $clip neither exported nor known-pending", clip in requiredClips || clip in pending)
        }
    }

    @Test
    fun pushUpPlaysDownThenUp() {
        assertEquals(listOf("pushup_down", "pushup_up"), DemoSequence.resolve("pushup_down", requiredClips))
    }

    @Test
    fun squatPlaysDownThenUp() {
        assertEquals(listOf("squat_down", "squat_up"), DemoSequence.resolve("squat_down", requiredClips))
    }

    @Test
    fun singleClipsPlayAlone() {
        assertEquals(listOf("boxing_jab"), DemoSequence.resolve("boxing_jab", requiredClips))
    }

    @Test
    fun `a footwork step plays with its return step so the drill loops in place`() {
        assertEquals(listOf("footwork_forward", "footwork_backward"), DemoSequence.resolve("footwork_forward", requiredClips))
        assertEquals(listOf("footwork_backward", "footwork_forward"), DemoSequence.resolve("footwork_backward", requiredClips))
        assertEquals(listOf("footwork_forward"), DemoSequence.resolve("footwork_forward", setOf("footwork_forward")))
    }

    @Test
    fun missingClipGivesEmptySequence() {
        assertEquals(emptyList<String>(), DemoSequence.resolve("not_a_clip_down", requiredClips))
        assertEquals(emptyList<String>(), DemoSequence.resolve(null, requiredClips))
    }

    @Test
    fun downWithoutUpPlaysAlone() {
        assertEquals(listOf("x_down"), DemoSequence.resolve("x_down", setOf("x_down")))
    }

    @Test
    fun locateWalksAndLoopsTheSequence() {
        val d = listOf(1.6f, 1.6f)
        assertEquals(0 to 0f, DemoSequence.locate(d, 0.0))
        assertEquals(0, DemoSequence.locate(d, 1.0).first)
        val second = DemoSequence.locate(d, 2.0)
        assertEquals(1, second.first)
        assertEquals(0.4f, second.second, 1e-4f)
        assertEquals(0, DemoSequence.locate(d, 3.3).first) // looped
        assertEquals(0 to 0f, DemoSequence.locate(d, -5.0))
    }

    @Test
    fun phaseLabels() {
        assertEquals("Lowering", DemoSequence.phaseLabel("squat_down"))
        assertEquals("Rising", DemoSequence.phaseLabel("squat_up"))
        assertEquals("Jab", DemoSequence.phaseLabel("boxing_jab"))
        assertEquals("Step forward", DemoSequence.phaseLabel("footwork_forward"))
        assertEquals("Step side to side", DemoSequence.phaseLabel("footwork_lateral"))
        assertEquals("Lead hook", DemoSequence.phaseLabel("boxing_lead_hook"))
        assertEquals("Hold", DemoSequence.phaseLabel("plank_hold"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun badManifestIsRejected() {
        ClipManifest.parse("""{"asset":"a.glb","clips":[{"name":"x","durationSeconds":0,"reviewStatus":"draft_pending_coach_review"}]}""")
    }

    @Test
    fun lessonsStartFromTheirRecommendedView() {
        assertEquals(ViewAngle.SIDE, defaultViewAngle("side"))
        assertEquals(ViewAngle.THREE_QUARTER, defaultViewAngle("front_or_diagonal"))
        assertEquals(ViewAngle.FRONT, defaultViewAngle("full_body"))
        assertEquals(ViewAngle.FRONT, defaultViewAngle(null))
    }

    @Test
    fun everyLessonHasA3dDemo() {
        val catalog = ExerciseCatalogParser.parse(File(assets, ExerciseCatalogParser.ASSET_PATH).readText())
        catalog.forEach { assertTrue("${it.id} has no demo", DemoSequence.resolve(it.demoAnimation, requiredClips).isNotEmpty()) }
    }

    @Test
    fun everyLessonHasCoachArtForBothCoaches() {
        val catalog = ExerciseCatalogParser.parse(File(assets, ExerciseCatalogParser.ASSET_PATH).readText())
        bundled.forEach { coach ->
            assertTrue("${coach.heroArt} missing", File(assets, coach.heroArt).isFile)
            catalog.forEach { assertTrue("${coach.lessonArt(it.id)} missing", File(assets, coach.lessonArt(it.id)).isFile) }
        }
    }
}
