package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.temporal.TemporalAdjusters

data class ExerciseRecord(val exerciseId: String, val name: String, val durationSeconds: Int, val repetitions: Int?, val trackingQuality: String)

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
)

/** Simple consistency numbers. No streaks, no pressure mechanics. */
object ProgressStats {
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
        return ProgressSummary(buckets.last().sessions, buckets.last().minutes, records.size, buckets)
    }

    /** Rounded to the nearest minute, but any non-empty training shows at least 1. */
    private fun minutes(list: List<SessionRecord>): Int {
        val seconds = list.sumOf { it.durationSeconds }
        return if (seconds == 0) 0 else maxOf(1, (seconds + 30) / 60)
    }
}
