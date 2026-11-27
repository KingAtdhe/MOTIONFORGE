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
        assertTrue(CountedMove.counterFor("boxing_pull_back") is TwoSidedRepCounter)
        assertTrue(CountedMove.counterFor("standing_oblique_crunch") is KneeLiftRepCounter)
        assertTrue(CountedMove.counterFor("dumbbell_squat") is SquatRepCounter)
        assertTrue(CountedMove.counterFor("dumbbell_reverse_lunge") is LungeRepCounter)
        // batch 7: each mapping is checked on rendered videos (RenderedVideoRepTest); everything else is guided only
        assertTrue(CountedMove.counterFor("dumbbell_goblet_squat") is SquatRepCounter)
        assertTrue(CountedMove.counterFor("curtsy_lunge") is LungeRepCounter)
        listOf("boxing_body_cross", "boxing_body_hook", "boxing_rear_body_hook").forEach {
            assertTrue(it, CountedMove.counterFor(it) is LevelChangeRepCounter)
        }
        listOf("boxing_jab_body_cross", "boxing_jab_uppercut", "boxing_uppercut_hook", "boxing_hook_cross", "boxing_cross_hook_cross",
            "boxing_one_two_uppercut", "boxing_uppercuts").forEach { assertTrue(it, CountedMove.counterFor(it) is ComboRepCounter) }
        listOf("boxing_back_jab", "boxing_lateral_jab", "boxing_jab_pivot").forEach { assertTrue(it, CountedMove.counterFor(it) is PunchRepCounter) }
        assertTrue(CountedMove.counterFor("boxing_jab_slip") is SlipRepCounter)
        // guard-only or held positions, and footwork (a guided drill, never scored): not counted
        listOf("boxing_parry", "boxing_catch", "boxing_high_block", "wall_sit", "forearm_plank", "hip_hinge",
            "footwork_circle_left", "footwork_forward_backward", "standing_mobility_warmup").forEach { assertNull(it, CountedMove.counterFor(it)) }
        // 2026-11-25: the rest of the catalogue, each checked on rendered videos
        assertTrue(CountedMove.counterFor("boxing_duck") is LevelChangeRepCounter)
        assertNull(CountedMove.counterFor("boxing_slip_cross"))   // guard check only: the cross at the phone barely lifts the elbow
        assertTrue(CountedMove.counterFor("kettlebell_swing") is SignalRepCounter)
        assertTrue(CountedMove.counterFor("calf_raise") is CalfRaiseRepCounter)
        listOf("crunch", "dead_bug", "bird_dog", "slow_mountain_climber", "wall_push_up").forEach { assertTrue(it, CountedMove.counterFor(it) is SignalRepCounter) }
        assertTrue(CountedMove.counterFor("standing_side_bend") is TwoSidedRepCounter)
        // 2026-11-27 mobility
        assertTrue(CountedMove.counterFor("leg_swings") is PendulumRepCounter)
        assertTrue(CountedMove.counterFor("hip_circles") is SignalRepCounter)
        assertNull(CountedMove.counterFor("standing_quad_stretch"))
    }

    /** Feeds a signal sequence (one value per 83 ms frame, null = unreadable) through a pendulum counter. */
    private fun pendulum(values: List<Double?>, maxRepMs: Long = 1_500): Int {
        val f = PoseFixtures.standingFrame(0)
        var i = 0
        val c = PendulumRepCounter(travel = 25.0, side = 8.0, maxRepMs = maxRepMs) { values[i] }
        values.indices.forEach { k -> i = k; c.update(f.copy(timestampMs = k * 83L), true) }
        return c.repetitions
    }

    @Test
    fun pendulumCountsEachCrossingNotOneSidedMoves() {
        // forward to -25, back to +20, forward, back: three changes of side
        val swing = listOf(0.0, -12.0, -25.0, -12.0, 0.0, 10.0, 20.0, 10.0, 0.0, -12.0, -25.0, -12.0, 0.0, 10.0, 20.0, 10.0, 0.0)
        assertEquals(3, pendulum(swing))
        // a heel kicked up behind (one side only) and back, several times: nothing
        assertEquals(0, pendulum(List(4) { listOf(0.0, 15.0, 30.0, 15.0, 0.0) }.flatten()))
        // too small a swing (under the travel) is not counted
        assertEquals(0, pendulum(listOf(0.0, -10.0, 0.0, 10.0, 0.0, -10.0, 0.0)))
        // a slow change of side (stepping into a split stance and out) is not a swing
        assertEquals(0, pendulum(listOf(-25.0) + List(30) { -25.0 } + listOf(0.0, 25.0)))
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
