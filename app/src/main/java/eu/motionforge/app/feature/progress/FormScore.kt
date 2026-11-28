package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.movement.CountedMove

/**
 * Reps with no possible form adjustment flagged, out of all attempts (counted reps plus attempts too shallow to
 * count). Only for the moves whose counters check form rules on every rep (squat, push-up and lunge families), and
 * only with enough reps that one odd rep cannot swing it ([FormScore.MIN_ATTEMPTS]). It describes what the camera's
 * few simple rules saw; it never certifies technique.
 */
data class FormTally(val clean: Int, val attempts: Int) {
    val percent: Int get() = if (attempts == 0) 0 else Math.round(100.0 * clean / attempts).toInt()
    operator fun plus(o: FormTally) = FormTally(clean + o.clean, attempts + o.attempts)
}

/** One exercise's form over time: [recent] percents oldest first (sets with enough reps only). */
data class FormTrend(val exerciseId: String, val name: String, val recent: List<Int>, val lastAtMillis: Long) {
    val last: Int get() = recent.last()
}

object FormScore {
    /** Fewer attempts than this in a set (or a session) give no score. */
    const val MIN_ATTEMPTS = 5
    const val RECENT = 8
    private val RULED = setOf(CountedMove.SQUAT, CountedMove.PUSH_UP, CountedMove.LUNGE)

    fun hasRules(exerciseId: String): Boolean = CountedMove.forExercise(exerciseId) in RULED

    /** One set; null when it wasn't measured or had too few attempts. */
    fun of(e: ExerciseRecord): FormTally? {
        val reps = e.repetitions ?: return null
        val clean = e.cleanReps ?: return null
        val t = FormTally(clean.coerceIn(0, reps), reps + (e.shallowReps ?: 0))
        return t.takeIf { it.attempts >= MIN_ATTEMPTS }
    }

    /** A whole session: every measured set summed; null below [MIN_ATTEMPTS] in total. */
    fun of(s: SessionRecord): FormTally? = ofSets(s.exercises)

    /** Several sets summed (a session, or the sets of a session that is just ending). */
    fun ofSets(exercises: List<ExerciseRecord>): FormTally? {
        val sets = exercises.mapNotNull { e ->
            val reps = e.repetitions ?: return@mapNotNull null
            val clean = e.cleanReps ?: return@mapNotNull null
            FormTally(clean.coerceIn(0, reps), reps + (e.shallowReps ?: 0))
        }
        if (sets.isEmpty()) return null
        return sets.reduce(FormTally::plus).takeIf { it.attempts >= MIN_ATTEMPTS }
    }

    /** Per exercise, most recently trained first. */
    fun trends(records: List<SessionRecord>): List<FormTrend> {
        val sets = records.sortedBy { it.startedAtMillis }.flatMap { s ->
            s.exercises.mapNotNull { e -> of(e)?.let { Triple(e, it.percent, s.startedAtMillis) } }
        }
        return sets.groupBy { it.first.exerciseId }.map { (id, list) ->
            FormTrend(id, list.last().first.name, list.map { it.second }.takeLast(RECENT), list.last().third)
        }.sortedByDescending { it.lastAtMillis }
    }
}
