package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.core.movement.HoldCheck

/**
 * Stretch & mobility flows: fixed follow-along sequences of the catalogue's mobility and stretch lessons, each move
 * for its own time with a short "next" transition. The camera counts or times a move only where that lesson already
 * has a validated check; everything else is guided by the timer.
 */
enum class Flow(val wire: String, val title: String, val detail: String, val moves: List<Pair<String, Int>>) {
    MORNING("morning", "Morning mobility", "Wake up the joints from head to toe, all standing.", listOf(
        "arm_circles" to 40, "standing_side_bend" to 40, "standing_torso_twist" to 40, "hip_circles" to 40,
        "leg_swings" to 45, "squat_hold" to 40, "standing_hamstring_stretch" to 50, "standing_calf_stretch" to 45,
    )),
    AFTER_TRAINING("cooldown", "After training", "Slow stretches for the legs, hips, chest and shoulders.", listOf(
        "standing_quad_stretch" to 50, "standing_hamstring_stretch" to 50, "standing_calf_stretch" to 45,
        "kneeling_hip_flexor_stretch" to 55, "chest_opener_stretch" to 40, "cross_body_shoulder_stretch" to 45,
        "overhead_triceps_stretch" to 45, "childs_pose" to 60,
    )),
    DESK_BREAK("desk", "Desk break", "A short break on your feet for the neck, shoulders, back and calves.", listOf(
        "arm_circles" to 35, "chest_opener_stretch" to 40, "cross_body_shoulder_stretch" to 40, "overhead_triceps_stretch" to 40,
        "standing_side_bend" to 35, "standing_torso_twist" to 35, "standing_calf_stretch" to 40,
    )),
    HIPS_BACK("hips", "Hips & lower back", "Gentle mobility for stiff hips and a tired lower back, mostly on the floor.", listOf(
        "cat_cow" to 50, "childs_pose" to 50, "hip_circles" to 40, "kneeling_hip_flexor_stretch" to 55, "leg_swings" to 40,
        "squat_hold" to 40, "standing_hamstring_stretch" to 50, "childs_pose" to 45,
    ));

    companion object {
        fun ofWire(w: String) = entries.firstOrNull { it.wire == w }
    }
}

object Flows {
    /** Seconds between moves: enough to read the next name and change position. */
    const val TRANSITION_SECONDS = 8

    fun key(f: Flow) = "flow-${f.wire}"

    fun parseKey(key: String): Flow? = if (key.startsWith("flow-")) Flow.ofWire(key.removePrefix("flow-")) else null

    /** Total length in whole minutes, rounded up (moves and transitions). */
    fun minutes(f: Flow): Int {
        val s = f.moves.sumOf { it.second } + TRANSITION_SECONDS * (f.moves.size - 1)
        return (s + 59) / 60
    }

    /** The session; moves missing from the catalogue are left out (null when none are there). */
    fun build(f: Flow, catalog: List<Exercise>): SessionPlan? {
        val byId = catalog.associateBy { it.id }
        val moves = f.moves.mapNotNull { (id, s) -> byId[id]?.let { it to s } }
        if (moves.isEmpty()) return null
        val steps = mutableListOf<SessionStep>()
        moves.forEachIndexed { i, (e, seconds) ->
            if (i > 0) steps += SessionStep.Rest(TRANSITION_SECONDS, e.name)
            steps += SessionStep.Work(
                e.id, e.name, seconds, countsReps = CountedMove.forExercise(e.id) != null, formDrill = null,
                holdCheck = HoldCheck.forExercise(e.id),
            )
        }
        return SessionPlan(f.title, TrainingCategory.FITNESS, steps)
    }
}
