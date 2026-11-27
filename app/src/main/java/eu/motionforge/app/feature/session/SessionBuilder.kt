package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.core.movement.HoldCheck

/** What a built session trains. [ids] are the lessons it draws from (any that exist in the catalogue). */
enum class SessionFocus(val wire: String, val label: String, val category: TrainingCategory, val ids: List<String>) {
    FULL_BODY("full", "Full body", TrainingCategory.FITNESS, emptyList()),          // a mix of the three lists below
    LEGS("legs", "Legs & glutes", TrainingCategory.FITNESS, listOf(
        "bodyweight_squat", "reverse_lunge", "glute_bridge", "sumo_squat", "split_squat", "side_lunge", "forward_lunge",
        "curtsy_lunge", "squat_calf_raise", "calf_raise", "wall_sit", "good_morning", "glute_kickback", "side_leg_raise",
        "single_leg_glute_bridge", "skater_step", "donkey_kick", "fire_hydrant", "single_leg_rdl",
        "dumbbell_squat", "dumbbell_goblet_squat", "dumbbell_reverse_lunge", "dumbbell_romanian_deadlift", "dumbbell_calf_raise",
    )),
    UPPER("upper", "Upper body", TrainingCategory.FITNESS, listOf(
        "knee_push_up", "incline_push_up", "wall_push_up", "push_up", "bench_dip", "plank_shoulder_taps", "arm_circles",
        "high_plank", "bear_plank_hold", "superman",
        "dumbbell_biceps_curl", "dumbbell_shoulder_press", "dumbbell_lateral_raise", "dumbbell_bent_over_row",
        "dumbbell_hammer_curl", "dumbbell_front_raise", "dumbbell_reverse_fly", "dumbbell_overhead_triceps_extension",
        "dumbbell_floor_press", "dumbbell_shrug",
    )),
    CORE("core", "Core", TrainingCategory.FITNESS, listOf(
        "forearm_plank", "dead_bug", "bird_dog", "crunch", "reverse_crunch", "heel_taps", "tabletop_toe_taps", "high_plank",
        "slow_mountain_climber", "superman", "bear_plank_hold", "standing_knee_crunch", "standing_oblique_crunch",
        "standing_side_bend", "standing_torso_twist",
    )),
    BOXING("boxing", "Boxing", TrainingCategory.FIGHTING_FUNDAMENTALS, emptyList()),  // every fighting lesson but footwork
    STRETCH("stretch", "Stretch & recover", TrainingCategory.FITNESS, listOf(
        "cat_cow", "childs_pose", "standing_quad_stretch", "cross_body_shoulder_stretch", "overhead_triceps_stretch",
        "chest_opener_stretch", "kneeling_hip_flexor_stretch", "standing_side_bend", "standing_torso_twist", "arm_circles",
    )),
    // appended last: Home keeps the chosen focus as an index
    ROUNDS("rounds", "Boxing rounds", TrainingCategory.FIGHTING_FUNDAMENTALS, emptyList()), // timed rounds, called combos
    ;

    companion object {
        fun ofWire(w: String) = entries.firstOrNull { it.wire == w }
    }
}

/**
 * "Build your own session": a focus, a length and whether there are dumbbells. Warm-up first, then moves from the
 * focus (a different order each day, so the same choice isn't the same workout every time), each about 40 s with 15 s
 * rests, then a short cool-down stretch for sessions of 10 minutes or more. Pure Kotlin, unit-tested.
 */
object SessionBuilder {
    val MINUTES = listOf(5, 10, 15, 20)
    private const val WARM_UP_ID = "standing_mobility_warmup"
    private val COOL_DOWN = listOf("standing_quad_stretch", "cross_body_shoulder_stretch", "kneeling_hip_flexor_stretch",
        "overhead_triceps_stretch", "chest_opener_stretch", "childs_pose")

    /** "build-<focus>-<minutes>-<d|n>-<day>": d = dumbbells. The day keeps a session the same after a restart. */
    fun key(focus: SessionFocus, minutes: Int, dumbbells: Boolean, day: Long) = "build-${focus.wire}-$minutes-${if (dumbbells) "d" else "n"}-$day"

    fun parseKey(key: String): Params? {
        val p = key.split('-')
        if (p.size != 5 || p[0] != "build") return null
        val focus = SessionFocus.ofWire(p[1]) ?: return null
        val minutes = p[2].toIntOrNull()?.takeIf { it in MINUTES } ?: return null
        val db = when (p[3]) { "d" -> true; "n" -> false; else -> return null }
        val day = p[4].toLongOrNull() ?: return null
        return Params(focus, minutes, db, day)
    }

    data class Params(val focus: SessionFocus, val minutes: Int, val dumbbells: Boolean, val day: Long)

    private fun usable(e: Exercise, dumbbells: Boolean): Boolean {
        val needs = e.equipment.filter { !it.contains("(optional)") && !it.contains("(recommended)") }
        return needs.all { dumbbells && it.startsWith("Dumbbell") }
    }

    private fun work(e: Exercise, seconds: Int) = SessionStep.Work(
        e.id, e.name, seconds, countsReps = CountedMove.forExercise(e.id) != null, formDrill = SessionPlanner.drillFor(e.id),
        holdCheck = HoldCheck.forExercise(e.id),
    )

    /** A stable shuffle for the day (a small LCG: the same day and focus always give the same order). */
    private fun <T> shuffled(list: List<T>, seed: Long): List<T> {
        var s = seed * 6364136223846793005L + 1442695040888963407L
        val out = list.toMutableList()
        for (i in out.indices.reversed()) {
            s = s * 6364136223846793005L + 1442695040888963407L
            val j = ((s ushr 33) % (i + 1)).toInt()
            val t = out[i]; out[i] = out[j]; out[j] = t
        }
        return out
    }

    fun build(catalog: List<Exercise>, p: Params): SessionPlan? {
        val byId = catalog.associateBy { it.id }
        val seed = p.day * 31 + p.focus.ordinal
        if (p.focus == SessionFocus.ROUNDS) return rounds(catalog, byId, p, seed)
        val pool: List<Exercise> = when (p.focus) {
            SessionFocus.FULL_BODY -> {
                // interleave legs, upper body and core so the session works everything
                val lists = listOf(SessionFocus.LEGS, SessionFocus.UPPER, SessionFocus.CORE).mapIndexed { i, f ->
                    shuffled(f.ids.mapNotNull { byId[it] }.filter { usable(it, p.dumbbells) }, seed + i)
                }
                (0 until lists.maxOf { it.size }).flatMap { i -> lists.mapNotNull { it.getOrNull(i) } }
                    .distinctBy { it.id } // planks and the superman are in both upper body and core
            }
            SessionFocus.BOXING -> {
                val all = catalog.filter { it.category == TrainingCategory.FIGHTING_FUNDAMENTALS && !it.id.startsWith("footwork_") }
                // the stance first, then the rest in the day's order
                val stance = all.filter { it.id == SessionPlanner.STANCE_ID }
                stance + shuffled(all - stance.toSet(), seed)
            }
            else -> shuffled(p.focus.ids.mapNotNull { byId[it] }.filter { usable(it, p.dumbbells) }, seed)
        }
        if (pool.isEmpty()) return null
        val target = p.minutes * 60
        val rest = SessionPlanner.REST_SECONDS
        val steps = mutableListOf<SessionStep>()
        var total = 0
        fun add(e: Exercise, seconds: Int) {
            if (steps.isNotEmpty()) { steps += SessionStep.Rest(rest, e.name); total += rest }
            steps += work(e, seconds); total += seconds
        }
        val stretching = p.focus == SessionFocus.STRETCH
        byId[WARM_UP_ID]?.takeIf { !stretching }?.let { add(it, if (p.minutes <= 10) 60 else 90) }
        val coolDown = if (p.minutes >= 10 && !stretching) {
            shuffled(COOL_DOWN.mapNotNull { byId[it] }, seed).take(if (p.minutes >= 15) 2 else 1)
        } else emptyList()
        val coolDownTime = coolDown.size * (45 + rest)
        val each = if (stretching) 50 else 40
        // a short list is gone through again in rounds (never the same move twice in a row)
        var last: String? = null
        rounds@ for (round in 0 until 4) for (e in pool) {
            if (total + rest + each + coolDownTime > target + 20) break@rounds
            if (e.id == last) continue
            add(e, each); last = e.id
        }
        // a short session still gets at least two moves
        if (steps.count { it is SessionStep.Work } < 2) pool.firstOrNull { it.id != last }?.let { add(it, each) }
        coolDown.forEach { add(it, 45) }
        return SessionPlan("${p.focus.label}, ${p.minutes} min", p.focus.category, steps)
    }

    /** Rest between rounds, and a round's length (shorter rounds in a 5-minute session). */
    const val ROUND_REST = 45
    fun roundSeconds(minutes: Int) = if (minutes <= 5) 90 else 120

    /**
     * Shadow-boxing rounds: warm-up, then as many rounds as fit (a bell at each start and end, combinations called out
     * every few seconds, the guard check with the camera), 45 s rest between, and a cool-down stretch from 10 min.
     */
    private fun rounds(catalog: List<Exercise>, byId: Map<String, Exercise>, p: Params, seed: Long): SessionPlan? {
        val lesson = byId[ShadowRounds.ROUND_LESSON] ?: return null
        val available = catalog.map { it.id }.toSet()
        val target = p.minutes * 60
        val rest = SessionPlanner.REST_SECONDS
        val len = roundSeconds(p.minutes)
        val steps = mutableListOf<SessionStep>()
        var total = 0
        val warm = byId[WARM_UP_ID]
        if (warm != null) { steps += work(warm, if (p.minutes <= 10) 60 else 90); total += steps.last().durationSeconds }
        val coolDown = if (p.minutes >= 10) shuffled(COOL_DOWN.mapNotNull { byId[it] }, seed).take(if (p.minutes >= 15) 2 else 1) else emptyList()
        val coolDownTime = coolDown.size * (45 + rest)
        var n = 0
        while (n == 0 || total + ROUND_REST + len + coolDownTime <= target + 20) {
            val r = n + 1
            if (steps.isNotEmpty()) { val gap = if (n == 0) rest else ROUND_REST; steps += SessionStep.Rest(gap, "Round $r"); total += gap }
            steps += work(lesson, len).copy(
                name = "Round $r",
                round = r,
                calls = ShadowRounds.callsFor(r, len, available, seed),
                callEverySeconds = ShadowRounds.CALL_EVERY_SECONDS,
            )
            total += len; n++
            if (n >= 8) break
        }
        coolDown.forEach { e -> steps += SessionStep.Rest(rest, e.name); steps += work(e, 45); total += rest + 45 }
        return SessionPlan("${p.focus.label}, ${p.minutes} min", p.focus.category, steps)
    }
}
