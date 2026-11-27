package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.temporal.TemporalAdjusters

data class ExerciseRecord(
    val exerciseId: String, val name: String, val durationSeconds: Int, val repetitions: Int?, val trackingQuality: String,
    /** Seconds held in position (hold checks), null when not measured. */
    val heldSeconds: Int? = null,
)

data class SessionRecord(
    val id: Long,
    val title: String,
    val type: TrainingCategory,
    val startedAtMillis: Long,
    val durationSeconds: Int,
    val perceivedEffort: Int?,
    val completed: Boolean,
    val exercises: List<ExerciseRecord>,
)

data class WeekBucket(val weekStart: LocalDate, val sessions: Int, val minutes: Int)

data class ProgressSummary(
    val sessionsThisWeek: Int,
    val minutesThisWeek: Int,
    val totalSessions: Int,
    /** Oldest first, always [weeks] long, ending with the current week. */
    val recentWeeks: List<WeekBucket>,
    /** Days of the current week (Mon–Sun) with at least one saved session. */
    val trainedDaysThisWeek: Set<DayOfWeek> = emptySet(),
)

/**
 * Camera-counted reps of one exercise over time. [recent] oldest first (at most [ProgressStats.RECENT] sets);
 * [best] over all saved sets; [newBest] = the latest set is the best so far and beat an earlier one.
 */
data class RepTrend(val exerciseId: String, val name: String, val recent: List<Int>, val best: Int, val lastAtMillis: Long) {
    val last: Int get() = recent.last()
    val newBest: Boolean get() = recent.size > 1 && last == best && recent.dropLast(1).all { it < last }
}

/** Simple consistency numbers. The calm weekly streak and badges live in [Milestones]. */
object ProgressStats {
    const val RECENT = 8

    /** One trend per exercise the camera has counted, most recently trained first. */
    fun repTrends(records: List<SessionRecord>): List<RepTrend> {
        val sets = records.sortedBy { it.startedAtMillis }.flatMap { s ->
            s.exercises.filter { it.repetitions != null }.map { Triple(it, it.repetitions!!, s.startedAtMillis) }
        }
        return sets.groupBy { it.first.exerciseId }.map { (id, list) ->
            val reps = list.map { it.second }
            RepTrend(id, list.last().first.name, reps.takeLast(RECENT), reps.max(), list.last().third)
        }.sortedByDescending { it.lastAtMillis }
    }

    /** Like [repTrends] for held positions: seconds held in position per set (sets with nothing held are left out). */
    fun holdTrends(records: List<SessionRecord>): List<RepTrend> {
        val sets = records.sortedBy { it.startedAtMillis }.flatMap { s ->
            s.exercises.filter { (it.heldSeconds ?: 0) > 0 }.map { Triple(it, it.heldSeconds!!, s.startedAtMillis) }
        }
        return sets.groupBy { it.first.exerciseId }.map { (id, list) ->
            val v = list.map { it.second }
            RepTrend(id, list.last().first.name, v.takeLast(RECENT), v.max(), list.last().third)
        }.sortedByDescending { it.lastAtMillis }
    }

    fun summarize(records: List<SessionRecord>, today: LocalDate, zone: ZoneId, weeks: Int = 4): ProgressSummary {
        require(weeks >= 1)
        val thisWeek = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
        fun weekOf(r: SessionRecord) = Instant.ofEpochMilli(r.startedAtMillis).atZone(zone).toLocalDate()
            .with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
        val byWeek = records.groupBy(::weekOf)
        val buckets = (weeks - 1 downTo 0).map { back ->
            val start = thisWeek.minusWeeks(back.toLong())
            val list = byWeek[start].orEmpty()
            WeekBucket(start, list.size, minutes(list))
        }
        val days = byWeek[thisWeek].orEmpty()
            .map { Instant.ofEpochMilli(it.startedAtMillis).atZone(zone).dayOfWeek }
            .toSet()
        return ProgressSummary(buckets.last().sessions, buckets.last().minutes, records.size, buckets, days)
    }

    /** Rounded to the nearest minute, but any non-empty training shows at least 1. */
    private fun minutes(list: List<SessionRecord>): Int {
        val seconds = list.sumOf { it.durationSeconds }
        return if (seconds == 0) 0 else maxOf(1, (seconds + 30) / 60)
    }
}
