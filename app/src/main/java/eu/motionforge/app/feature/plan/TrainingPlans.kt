package eu.motionforge.app.feature.plan

import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.feature.progress.SessionRecord
import eu.motionforge.app.feature.session.SessionPlan
import eu.motionforge.app.feature.session.SessionPlanner
import eu.motionforge.app.feature.session.SessionStep

/**
 * One exercise in a plan day. [reps] = the plan's rep target for each week (camera-counted moves); the step ends when
 * the camera counts it, with a time cap. Without [reps] (or without a counter) the step is timed: [seconds].
 */
data class PlanItem(val exerciseId: String, val seconds: Int, val reps: List<Int>? = null)

data class PlanDay(val label: String, val items: List<PlanItem>)

data class TrainingPlan(
    val id: String,
    val name: String,
    val summary: String,
    val category: TrainingCategory,
    val needsEquipment: Boolean,
    val weeks: Int,
    val sessionsPerWeek: Int,
    /** Days alternate A, B, A… through the plan. */
    val days: List<PlanDay>,
) {
    val totalSessions: Int get() = weeks * sessionsPerWeek

    fun weekOf(index: Int): Int = (index / sessionsPerWeek).coerceIn(0, weeks - 1)
    fun dayOf(index: Int): PlanDay = days[index % days.size]
}

object TrainingPlans {
    private fun r(vararg w: Int) = w.toList()

    val FOUNDATIONS = TrainingPlan(
        id = "foundations", name = "Foundations",
        summary = "Four weeks of squats, push-ups, lunges and bridges. No equipment. Three short sessions a week.",
        category = TrainingCategory.FITNESS, needsEquipment = false, weeks = 4, sessionsPerWeek = 3,
        days = listOf(
            PlanDay("A", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("bodyweight_squat", 60, r(8, 10, 12, 14)),
                PlanItem("knee_push_up", 60, r(6, 8, 10, 12)),
                PlanItem("reverse_lunge", 60, r(6, 8, 10, 12)),
                PlanItem("glute_bridge", 60, r(10, 12, 14, 16)),
            )),
            PlanDay("B", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("sumo_squat", 60, r(8, 10, 12, 14)),
                PlanItem("incline_push_up", 60, r(6, 8, 10, 12)),
                PlanItem("split_squat", 60, r(6, 8, 10, 12)),
                PlanItem("step_jack", 45, r(10, 14, 18, 22)),
            )),
        ),
    )

    val BOXING_BASICS = TrainingPlan(
        id = "boxing-basics", name = "Boxing basics",
        summary = "Four weeks building from the stance and jab to hooks, uppercuts and slips. Three sessions a week.",
        category = TrainingCategory.FIGHTING_FUNDAMENTALS, needsEquipment = false, weeks = 4, sessionsPerWeek = 3,
        days = listOf(
            PlanDay("A", listOf(
                PlanItem("boxing_stance", 45),
                PlanItem("boxing_jab", 45),
                PlanItem("boxing_double_jab", 60, r(6, 8, 10, 12)),
                PlanItem("boxing_lead_hook", 60, r(6, 8, 10, 12)),
                PlanItem("boxing_slip", 45, r(6, 8, 10, 12)),
            )),
            PlanDay("B", listOf(
                PlanItem("boxing_stance", 45),
                PlanItem("boxing_one_two", 60, r(6, 8, 10, 12)),
                PlanItem("boxing_cross_hook", 60, r(6, 8, 10, 12)),
                PlanItem("boxing_lead_uppercut", 60, r(6, 8, 10, 12)),
                PlanItem("boxing_rear_hook", 60, r(6, 8, 10, 12)),
            )),
        ),
    )

    val DUMBBELL_STRENGTH = TrainingPlan(
        id = "dumbbell-strength", name = "Dumbbell strength",
        summary = "Four weeks with a pair of light dumbbells: curls, presses, rows and hinges. Three sessions a week.",
        category = TrainingCategory.FITNESS, needsEquipment = true, weeks = 4, sessionsPerWeek = 3,
        days = listOf(
            PlanDay("A", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("dumbbell_squat", 60, r(8, 10, 12, 12)),
                PlanItem("dumbbell_biceps_curl", 60, r(8, 10, 12, 12)),
                PlanItem("dumbbell_shoulder_press", 60, r(8, 10, 10, 12)),
                PlanItem("dumbbell_romanian_deadlift", 60, r(8, 10, 12, 12)),
            )),
            PlanDay("B", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("dumbbell_reverse_lunge", 60, r(6, 8, 10, 12)),
                PlanItem("dumbbell_bent_over_row", 60, r(8, 10, 12, 12)),
                PlanItem("dumbbell_lateral_raise", 60, r(8, 10, 10, 12)),
                PlanItem("dumbbell_hammer_curl", 60, r(8, 10, 12, 12)),
                PlanItem("dumbbell_romanian_deadlift", 60, r(8, 10, 12, 12)),
            )),
        ),
    )

    val CORE_MOBILITY = TrainingPlan(
        id = "core-mobility", name = "Core & mobility",
        summary = "Four weeks of planks, dead bugs, bird dogs and stretches for a steadier middle and easier movement. No equipment.",
        category = TrainingCategory.FITNESS, needsEquipment = false, weeks = 4, sessionsPerWeek = 3,
        days = listOf(
            PlanDay("A", listOf(
                PlanItem("cat_cow", 45, r(5, 6, 7, 8)),
                PlanItem("dead_bug", 60, r(6, 8, 10, 12)),
                PlanItem("forearm_plank", 40),
                PlanItem("bird_dog", 60, r(6, 8, 10, 12)),
                PlanItem("kneeling_hip_flexor_stretch", 60),
                PlanItem("childs_pose", 45),
            )),
            PlanDay("B", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("crunch", 60, r(8, 10, 12, 14)),
                PlanItem("high_plank", 40),
                PlanItem("superman", 60, r(6, 8, 10, 12)),
                PlanItem("standing_side_bend", 45, r(6, 8, 8, 10)),
                PlanItem("cross_body_shoulder_stretch", 50),
            )),
        ),
    )

    val LEGS_GLUTES = TrainingPlan(
        id = "legs-glutes", name = "Legs & glutes",
        summary = "Four weeks of squats, lunges, bridges and balance work, finishing with a stretch. No equipment.",
        category = TrainingCategory.FITNESS, needsEquipment = false, weeks = 4, sessionsPerWeek = 3,
        days = listOf(
            PlanDay("A", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("bodyweight_squat", 60, r(10, 12, 14, 16)),
                PlanItem("glute_bridge", 60, r(10, 12, 14, 16)),
                PlanItem("side_lunge", 60, r(6, 8, 10, 12)),
                PlanItem("calf_raise", 45, r(10, 12, 14, 16)),
                PlanItem("standing_quad_stretch", 60),
            )),
            PlanDay("B", listOf(
                PlanItem("standing_mobility_warmup", 60),
                PlanItem("reverse_lunge", 60, r(6, 8, 10, 12)),
                PlanItem("single_leg_glute_bridge", 60, r(4, 6, 8, 10)),
                PlanItem("wall_sit", 40),
                PlanItem("glute_kickback", 60, r(6, 8, 10, 12)),
                PlanItem("kneeling_hip_flexor_stretch", 60),
            )),
        ),
    )

    val BOXING_CONDITIONING = TrainingPlan(
        id = "boxing-conditioning", name = "Boxing conditioning",
        summary = "Four weeks after the basics: combinations, defence and body shots, then a stretch. Three sessions a week.",
        category = TrainingCategory.FIGHTING_FUNDAMENTALS, needsEquipment = false, weeks = 4, sessionsPerWeek = 3,
        days = listOf(
            PlanDay("A", listOf(
                PlanItem("boxing_stance_bounce", 45),
                PlanItem("boxing_jab_jab_cross", 60, r(5, 6, 8, 10)),
                PlanItem("boxing_slip", 45, r(8, 10, 12, 14)),
                PlanItem("boxing_body_jab", 60, r(6, 8, 10, 12)),
                PlanItem("boxing_one_two_hook", 60, r(4, 6, 8, 10)),
                PlanItem("cross_body_shoulder_stretch", 50),
            )),
            PlanDay("B", listOf(
                PlanItem("boxing_stance_bounce", 45),
                PlanItem("boxing_duck", 45, r(6, 8, 10, 12)),
                PlanItem("boxing_hook_cross", 60, r(4, 6, 8, 10)),
                PlanItem("boxing_pull_counter", 60, r(4, 6, 8, 10)),
                PlanItem("boxing_uppercuts", 60, r(4, 6, 8, 10)),
                PlanItem("chest_opener_stretch", 45),
            )),
        ),
    )

    val ALL = listOf(FOUNDATIONS, BOXING_BASICS, DUMBBELL_STRENGTH, CORE_MOBILITY, LEGS_GLUTES, BOXING_CONDITIONING)

    fun byId(id: String?): TrainingPlan? = ALL.firstOrNull { it.id == id }

    /** Session route key for a plan session: "plan-<id>-<index>". */
    fun key(plan: TrainingPlan, index: Int) = "plan-${plan.id}-$index"

    fun parseKey(key: String): Pair<TrainingPlan, Int>? {
        if (!key.startsWith("plan-")) return null
        val rest = key.removePrefix("plan-")
        val cut = rest.lastIndexOf('-')
        if (cut <= 0) return null
        val plan = byId(rest.substring(0, cut)) ?: return null
        val index = rest.substring(cut + 1).toIntOrNull() ?: return null
        return if (index in 0 until plan.totalSessions) plan to index else null
    }
}

/**
 * How rep targets move. The plan sets a floor for each week; past that, the target is one more than the last time the
 * camera counted that exercise, so it follows what the person actually does. Never more than [MAX_ABOVE_PLAN] above
 * the plan's number: a single big day doesn't run away with the targets.
 */
object PlanProgression {
    const val MAX_ABOVE_PLAN = 6

    fun target(item: PlanItem, week: Int, history: List<SessionRecord>): Int? {
        val reps = item.reps ?: return null
        if (CountedMove.forExercise(item.exerciseId) == null) return null
        val base = reps[week.coerceIn(0, reps.lastIndex)]
        val last = lastCounted(item.exerciseId, history) ?: return base
        return maxOf(base, last + 1).coerceAtMost(base + MAX_ABOVE_PLAN)
    }

    /** The most recent camera-counted rep number for the exercise, or null. */
    fun lastCounted(exerciseId: String, history: List<SessionRecord>): Int? =
        history.sortedByDescending { it.startedAtMillis }
            .firstNotNullOfOrNull { s -> s.exercises.lastOrNull { it.exerciseId == exerciseId && it.repetitions != null }?.repetitions }

    /** Time cap for a rep-target step: about 4 s a rep plus setting up, never under the plan's own time. */
    fun capSeconds(item: PlanItem, target: Int?): Int = if (target == null) item.seconds else maxOf(item.seconds, target * 4 + 15)
}

object PlanSessions {
    /** The session for plan session [index], with targets from [history]; null if an exercise is missing. */
    fun build(plan: TrainingPlan, index: Int, catalog: List<Exercise>, history: List<SessionRecord>): SessionPlan? {
        val byId = catalog.associateBy { it.id }
        val week = plan.weekOf(index)
        val day = plan.dayOf(index)
        val steps = buildList {
            day.items.forEachIndexed { i, item ->
                val ex = byId[item.exerciseId] ?: return null
                if (i > 0) add(SessionStep.Rest(SessionPlanner.REST_SECONDS, ex.name))
                val target = PlanProgression.target(item, week, history)
                add(
                    SessionStep.Work(
                        ex.id, ex.name, PlanProgression.capSeconds(item, target),
                        countsReps = CountedMove.forExercise(ex.id) != null,
                        formDrill = SessionPlanner.drillFor(ex.id),
                        holdCheck = eu.motionforge.app.core.movement.HoldCheck.forExercise(ex.id),
                        targetReps = target,
                    ),
                )
            }
        }
        return SessionPlan("${plan.name} · week ${week + 1}, day ${day.label}", plan.category, steps)
    }
}
