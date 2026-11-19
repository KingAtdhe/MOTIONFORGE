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
    private val manifest = ClipManifest.parse(File(assets, ClipManifest.TRAINER_MANIFEST_PATH).readText())

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
        eu.motionforge.app.core.model.Coach.entries.forEach { coach ->
            val m = ClipManifest.parse(File(assets, coach.manifestPath).readText())
            val glb = File(assets, m.assetPath)
            assertTrue("GLB missing for $coach: $glb", glb.exists())
            assertEquals("clips of $coach", m.names, glbAnimationNames(glb))
        }
    }

    @Test
    fun everyCoachHasTheSameClips() {
        val sets = eu.motionforge.app.core.model.Coach.entries.map { ClipManifest.parse(File(assets, it.manifestPath).readText()).names }
        sets.forEach { assertEquals(sets.first(), it) }
    }

    @Test
    fun allClipsAreMarkedDraftUntilCoachReview() {
        manifest.clips.forEach { assertEquals(it.name, ReviewStatus.DRAFT_PENDING_COACH_REVIEW, it.reviewStatus) }
    }

    @Test
    fun everyLessonEitherHasItsClipOrIsKnownToBePending() {
        val pending = emptySet<String>()
        val catalog = ExerciseCatalogParser.parse(File(assets, ExerciseCatalogParser.ASSET_PATH).readText())
        catalog.mapNotNull { it.demoAnimation }.forEach { clip ->
            assertTrue("clip $clip neither exported nor known-pending", clip in manifest.names || clip in pending)
        }
    }

    @Test
    fun pushUpPlaysDownThenUp() {
        assertEquals(listOf("pushup_down", "pushup_up"), DemoSequence.resolve("pushup_down", manifest.names))
    }

    @Test
    fun squatPlaysDownThenUp() {
        assertEquals(listOf("squat_down", "squat_up"), DemoSequence.resolve("squat_down", manifest.names))
    }

    @Test
    fun singleClipsPlayAlone() {
        assertEquals(listOf("boxing_jab"), DemoSequence.resolve("boxing_jab", manifest.names))
    }

    @Test
    fun missingClipGivesEmptySequence() {
        assertEquals(emptyList<String>(), DemoSequence.resolve("not_a_clip_down", manifest.names))
        assertEquals(emptyList<String>(), DemoSequence.resolve(null, manifest.names))
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
        catalog.forEach { assertTrue("${it.id} has no demo", DemoSequence.resolve(it.demoAnimation, manifest.names).isNotEmpty()) }
    }

    @Test
    fun everyLessonHasCoachArtForBothCoaches() {
        val catalog = ExerciseCatalogParser.parse(File(assets, ExerciseCatalogParser.ASSET_PATH).readText())
        eu.motionforge.app.core.model.Coach.entries.forEach { coach ->
            assertTrue("${coach.heroArt} missing", File(assets, coach.heroArt).isFile)
            catalog.forEach { assertTrue("${coach.lessonArt(it.id)} missing", File(assets, coach.lessonArt(it.id)).isFile) }
        }
    }
}
