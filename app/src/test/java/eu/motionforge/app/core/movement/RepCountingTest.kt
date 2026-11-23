package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.PoseFixtures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin

class RepCountingTest {

    @Test
    fun everyCountedLessonHasACounter() {
        listOf("bodyweight_squat", "sumo_squat", "push_up", "knee_push_up", "incline_push_up", "reverse_lunge", "split_squat").forEach {
            assertTrue(it, CountedMove.counterFor(it) != null)
        }
        assertNull(CountedMove.counterFor("forearm_plank"))
        assertTrue(CountedMove.counterFor("bodyweight_squat") is SquatRepCounter)
        assertTrue(CountedMove.counterFor("knee_push_up") is PushUpRepCounter)
        assertTrue(CountedMove.counterFor("split_squat") is LungeRepCounter)
        assertTrue(CountedMove.counterFor("boxing_jab_jab_cross") is ComboRepCounter)
        assertTrue(CountedMove.counterFor("standing_knee_crunch") is KneeLiftRepCounter)
        assertTrue(CountedMove.counterFor("high_knee_march") is KneeLiftRepCounter)
        assertTrue(CountedMove.counterFor("dumbbell_overhead_triceps_extension") is OverheadDropRepCounter)
        assertTrue(CountedMove.counterFor("dumbbell_reverse_fly") is RowRepCounter)
        assertTrue(CountedMove.counterFor("boxing_double_jab") is ComboRepCounter)
        assertTrue(CountedMove.counterFor("boxing_cross_hook") is ComboRepCounter)
        assertTrue(CountedMove.counterFor("boxing_body_jab") is LevelChangeRepCounter)
        assertTrue(CountedMove.counterFor("boxing_step_jab") is PunchRepCounter)
        assertNull(CountedMove.counterFor("boxing_pull_back"))
        assertTrue(CountedMove.counterFor("standing_oblique_crunch") is KneeLiftRepCounter)
        assertTrue(CountedMove.counterFor("dumbbell_squat") is SquatRepCounter)
        assertTrue(CountedMove.counterFor("dumbbell_reverse_lunge") is LungeRepCounter)
    }

    /** Standing person bending and straightening both elbows (a curl): must never count as push-ups. */
    @Test
    fun armsBendingWhileStandingAreNotPushUps() {
        val c = PushUpRepCounter()
        var t = 0L
        repeat(4) {
            for (deg in (180 downTo 60 step 10) + (60..180 step 10)) {
                val a = Math.toRadians(180.0 - deg)
                // upper arm hangs down from the shoulder, the forearm swings forward/up by the elbow angle
                fun arm(sx: Float, sy: Float) = Triple(sx to sy, sx to (sy + 0.13f), (sx + (0.12 * sin(a)).toFloat()) to (sy + 0.13f + (0.12 * cos(a)).toFloat()))
                val (ls, le, lw) = arm(0.58f, 0.25f)
                val (rs, re, rw) = arm(0.42f, 0.25f)
                val f = PoseFixtures.standingFrame(t, mapOf(
                    BodyLandmark.LEFT_ELBOW to PoseFixtures.landmark(le.first, le.second), BodyLandmark.LEFT_WRIST to PoseFixtures.landmark(lw.first, lw.second),
                    BodyLandmark.RIGHT_ELBOW to PoseFixtures.landmark(re.first, re.second), BodyLandmark.RIGHT_WRIST to PoseFixtures.landmark(rw.first, rw.second),
                ))
                c.update(f, true); t += 66
            }
        }
        assertEquals(0, c.repetitions)
    }

    @Test
    fun trackingLossNeverCompletesARep() {
        val c = LungeRepCounter()
        val f = PoseFixtures.standingFrame(0)
        c.update(f, true)
        assertNull(c.update(f.copy(timestampMs = 66), tracking = false).angle)
        // a short blip keeps the state; a gap over MAX_BLIP_MS drops it
        assertEquals(RepPhase.UNKNOWN, c.update(f.copy(timestampMs = 66 + MAX_BLIP_MS + 100), tracking = false).phase)
    }
}
