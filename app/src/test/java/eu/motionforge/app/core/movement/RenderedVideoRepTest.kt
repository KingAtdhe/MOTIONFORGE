package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseOutput
import eu.motionforge.app.core.pose.TrackingStateEvaluator
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.zip.GZIPInputStream

/**
 * End-to-end check of the camera counting on real pose-model output.
 *
 * Each fixture is a video rendered in Blender of one of the app's own 3D coaches doing a known number of reps
 * (both coaches; front, side and 3/4 views; phone-like camera at ~1 m height), run through the same
 * pose_landmarker_lite model the app ships with (tools/pose_tests/, see docs/BUILD_LOG.md). The landmarks then go
 * through exactly what the session does: the full-body tracking gate, then the rep counter or boxing monitor.
 * Negative fixtures (marching, holding the stance) must count nothing.
 *
 * pose_fixtures/expected.txt: name|exercise id|expected count  (for boxing_jab the count is jabs)
 */
class RenderedVideoRepTest {

    private fun frames(name: String): List<PoseFrame?> {
        val stream = javaClass.classLoader!!.getResourceAsStream("pose_fixtures/$name.lm.gz") ?: error("missing fixture $name")
        return GZIPInputStream(stream).bufferedReader().readLines().filter { it.isNotBlank() }.map { line ->
            val p = line.split(' ')
            val t = p[0].toLong(); val w = p[1].toInt(); val h = p[2].toInt()
            if (p[3] == "none") null else {
                val v = p.subList(3, p.size).map { it.toFloat() }
                PoseFrame(List(33) { i -> Landmark(v[i * 5], v[i * 5 + 1], v[i * 5 + 2], v[i * 5 + 3], v[i * 5 + 4]) }, t, w, h, false)
            }
        }
    }

    private data class Result(val name: String, val exercise: String, val expected: Int, val got: Int, val detail: String)

    private fun run(name: String, exercise: String, expected: Int): Result {
        val fs = frames(name)
        val gate = TrackingStateEvaluator(TrackingStateEvaluator.FULL_BODY, eitherSide = true)
        val counter = CountedMove.counterFor(exercise)
        val drill = when (exercise) { "boxing_jab" -> BoxingDrill.JAB; "boxing_stance" -> BoxingDrill.STANCE; else -> null }
        val monitor = drill?.let { BoxingFormMonitor(it) }
        var tracked = 0
        val events = mutableListOf<String>()
        val cues = mutableSetOf<String>()
        fs.forEachIndexed { i, f ->
            val out = if (f == null) PoseOutput.NoPerson(i * 66L, 10) else PoseOutput.Detected(f, 10)
            val ok = gate.update(out).allowsFeedback
            if (ok) tracked++
            if (f != null) {
                counter?.update(f, ok)?.event?.let { ev ->
                    events += when (ev) {
                        is RepEvent.RepCompleted -> "rep${ev.rep}" + if (ev.issues.isEmpty()) "" else ev.issues.joinToString(",", "[", "]") { (it as Enum<*>).name }
                        RepEvent.ShallowRep -> "shallow"
                    }
                }
                monitor?.update(f, ok)?.let { fb -> if (fb is FormFeedback.Cue) cues += fb.issue.name }
            }
        }
        val got = counter?.repetitions ?: monitor?.jabs ?: -1
        return Result(name, exercise, expected, got, "tracked $tracked/${fs.size} ${events.joinToString(" ")} ${cues.joinToString(",", "cues[", "]")}")
    }

    @Test
    fun countsMatchRenderedVideos() {
        val spec = javaClass.classLoader!!.getResourceAsStream("pose_fixtures/expected.txt")!!.bufferedReader().readLines()
            .filter { it.isNotBlank() && !it.startsWith("#") }
        val results = spec.map { l -> val (n, e, c) = l.split('|'); run(n, e, c.trim().toInt()) }
        val table = results.joinToString("\n") { r -> "${if (r.got == r.expected) "ok  " else "FAIL"} ${r.name} (${r.exercise}) expected ${r.expected} got ${r.got} | ${r.detail}" }
        println(table)
        assertTrue("Rendered-video counts:\n$table", results.all { it.got == it.expected })
        // the coaches lower with control: no rep of theirs may be called rushed
        // the coaches demonstrate good form: no rep of theirs may get a correction, and the boxing coach no cue
        assertTrue("A correct coach demo got a form correction:\n$table", results.none { "[" in it.detail.substringBefore("cues[") || !it.detail.endsWith("cues[]") })
    }
}
