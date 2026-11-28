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
        "single_leg_glute_bridge", "skater_step", "donkey_kick", "fire_hydrant", "single_leg_rdl", "jump_squat",
        "dumbbell_squat", "dumbbell_goblet_squat", "dumbbell_reverse_lunge", "dumbbell_romanian_deadlift", "dumbbell_calf_raise",
    )),
    UPPER("upper", "Upper body", TrainingCategory.FITNESS, listOf(
        "knee_push_up", "incline_push_up", "wall_push_up", "push_up", "bench_dip", "plank_shoulder_taps", "arm_circles",
        "high_plank", "bear_plank_hold", "superman", "close_grip_push_up",
        "dumbbell_biceps_curl", "dumbbell_shoulder_press", "dumbbell_lateral_raise", "dumbbell_bent_over_row",
        "dumbbell_hammer_curl", "dumbbell_front_raise", "dumbbell_reverse_fly", "dumbbell_overhead_triceps_extension",
        "dumbbell_floor_press", "dumbbell_shrug",
    )),
    CORE("core", "Core", TrainingCategory.FITNESS, listOf(
        "forearm_plank", "dead_bug", "bird_dog", "crunch", "reverse_crunch", "heel_taps", "tabletop_toe_taps", "high_plank",
        "slow_mountain_climber", "superman", "bear_plank_hold", "standing_knee_crunch", "standing_oblique_crunch",
        "standing_side_bend", "standing_torso_twist",
        "hollow_hold", "bent_knee_leg_raise", "bicycle_crunch", "glute_bridge_march", "side_plank_knees",
        "plank_leg_lift", "side_plank",
    )),
    BOXING("boxing", "Boxing", TrainingCategory.FIGHTING_FUNDAMENTALS, emptyList()),  // every fighting lesson but footwork
    STRETCH("stretch", "Stretch & recover", TrainingCategory.FITNESS, listOf(
        "cat_cow", "childs_pose", "standing_quad_stretch", "cross_body_shoulder_stretch", "overhead_triceps_stretch",
        "chest_opener_stretch", "kneeling_hip_flexor_stretch", "standing_side_bend", "standing_torso_twist", "arm_circles",
        "leg_swings", "hip_circles", "standing_hamstring_stretch", "squat_hold", "standing_calf_stretch",
    )),
    // appended last: Home keeps the chosen focus as an index
    ROUNDS("rounds", "Boxing rounds", TrainingCategory.FIGHTING_FUNDAMENTALS, emptyList()), // timed rounds, called combos
    // intervals: short work, short rest; low-impact moves at level 1, jumps from level 2 (SessionBuilder.cardioSuits)
    CARDIO("cardio", "Cardio & HIIT", TrainingCategory.FITNESS, listOf(
        "step_jack", "high_knee_march", "butt_kicks", "skater_step", "slow_mountain_climber", "fast_feet", "boxing_speed_punches",
        "jumping_jack", "high_knees", "butt_kick_jog", "skater_hop", "plank_jack", "mountain_climber",
    )),
    ;

    companion object {
        fun ofWire(w: String) = entries.firstOrNull { it.wire == w }
    }
}

/**
 * "Build your own session": a focus, a length and whether there are dumbbells. Warm-up first, then moves from the
 * focus (a different order each day, so the same choice isn't the same workout every time), 40–50 s by level ([levelFor]) with 15 s
 * rests, then a short cool-down stretch for sessions of 10 minutes or more. Pure Kotlin, unit-tested.
 */
object SessionBuilder {
    val MINUTES = listOf(5, 10, 15, 20)
    private const val WARM_UP_ID = "standing_mobility_warmup"
    private val COOL_DOWN = listOf("standing_quad_stretch", "cross_body_shoulder_stretch", "kneeling_hip_flexor_stretch",
        "overhead_triceps_stretch", "chest_opener_stretch", "childs_pose", "standing_hamstring_stretch", "standing_calf_stretch")

    /**
     * "build-<focus>-<minutes>-<d|n>-<day>-L<level>": d = dumbbells. The day and level keep a session the same after a
     * restart (keys from before levels, without "-L…", read as level 1).
     */
    fun key(focus: SessionFocus, minutes: Int, dumbbells: Boolean, day: Long, level: Int = 1) =
        "build-${focus.wire}-$minutes-${if (dumbbells) "d" else "n"}-$day-L$level"

    fun parseKey(key: String): Params? {
        val p = key.split('-')
        if (p.size !in 5..6 || p[0] != "build") return null
        val focus = SessionFocus.ofWire(p[1]) ?: return null
        val minutes = p[2].toIntOrNull()?.takeIf { it in MINUTES } ?: return null
        val db = when (p[3]) { "d" -> true; "n" -> false; else -> return null }
        val day = p[4].toLongOrNull() ?: return null
        val level = if (p.size == 6) p[5].removePrefix("L").toIntOrNull()?.takeIf { it in LEVELS } ?: return null else 1
        return Params(focus, minutes, db, day, level)
    }

    data class Params(val focus: SessionFocus, val minutes: Int, val dumbbells: Boolean, val day: Long, val level: Int = 1)

    /**
     * Sessions get harder as you train: the level comes from sessions finished in the last [LEVEL_WINDOW_DAYS] days
     * (0–3 → 1, 4–9 → 2, 10+ → 3), so it also eases back after a break. Level 1: 40 s moves, the hardest variants left
     * out; level 2: 45 s, every move; level 3: 50 s and the easiest variants (wall / knee push-ups) left out.
     */
    val LEVELS = 1..3
    const val LEVEL_WINDOW_DAYS = 42
    fun levelFor(completedSessionStarts: List<Long>, nowMillis: Long): Int {
        val since = nowMillis - LEVEL_WINDOW_DAYS * 24L * 60 * 60 * 1000
        val n = completedSessionStarts.count { it in since..nowMillis }
        return when { n >= 10 -> 3; n >= 4 -> 2; else -> 1 }
    }
    /** Sessions needed in the window for the next level, or null at the top. */
    fun sessionsForNextLevel(level: Int): Int? = when (level) { 1 -> 4; 2 -> 10; else -> null }
    fun workSeconds(level: Int) = when (level) { 3 -> 50; 2 -> 45; else -> 40 }
    /** Rest between rounds in boxing rounds, by level. */
    fun roundRest(level: Int) = when (level) { 3 -> 30; 2 -> 40; else -> 45 }
    private val HARD_ONLY = setOf("push_up", "single_leg_rdl", "single_leg_glute_bridge", "skater_step", "bench_dip",
        "side_plank", "plank_leg_lift")
    private val EASY_ONLY = setOf("wall_push_up", "knee_push_up", "side_plank_knees")
    private fun suits(id: String, level: Int) = when (level) { 1 -> id !in HARD_ONLY; 3 -> id !in EASY_ONLY; else -> true }

    /** Cardio: jumps only from level 2 (the hardest three from level 3); level 3 drops the low-impact versions. */
    private val CARDIO_JUMPS = setOf("jumping_jack", "high_knees", "butt_kick_jog")
    private val CARDIO_HARD = setOf("skater_hop", "plank_jack", "mountain_climber")
    private val CARDIO_LOW = setOf("step_jack", "high_knee_march", "butt_kicks", "skater_step", "slow_mountain_climber")
    fun cardioSuits(id: String, level: Int) = when (level) {
        1 -> id !in CARDIO_JUMPS && id !in CARDIO_HARD
        2 -> id !in CARDIO_HARD
        else -> id !in CARDIO_LOW
    }
    /** Interval work and rest (seconds) in Cardio & HIIT, by level. */
    fun intervalWork(level: Int) = when (level) { 3 -> 40; 2 -> 35; else -> 30 }
    fun intervalRest(level: Int) = when (level) { 3 -> 15; 2 -> 20; else -> 30 }

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
            SessionFocus.CARDIO -> shuffled(p.focus.ids.mapNotNull { byId[it] }.filter { cardioSuits(it.id, p.level) }, seed)
            else -> shuffled(p.focus.ids.mapNotNull { byId[it] }.filter { usable(it, p.dumbbells) }, seed)
        }.filter { p.focus == SessionFocus.CARDIO || suits(it.id, p.level) }
            // level 1 keeps to beginner lessons (intermediate ones come from level 2)
            .filter { p.level > 1 || it.level == eu.motionforge.app.core.model.Level.BEGINNER }
        if (pool.isEmpty()) return null
        val target = p.minutes * 60
        val cardio = p.focus == SessionFocus.CARDIO
        val rest = if (cardio) intervalRest(p.level) else SessionPlanner.REST_SECONDS
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
        val each = when { stretching -> 50; cardio -> intervalWork(p.level); else -> workSeconds(p.level) }
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

    /** A round's length (shorter rounds in a 5-minute session). */
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
        val roundRest = roundRest(p.level)
        while (n == 0 || total + roundRest + len + coolDownTime <= target + 20) {
            val r = n + 1
            if (steps.isNotEmpty()) { val gap = if (n == 0) rest else roundRest; steps += SessionStep.Rest(gap, "Round $r"); total += gap }
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
