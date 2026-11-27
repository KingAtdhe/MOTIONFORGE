package eu.motionforge.app.feature.reminders

import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime

/**
 * When the optional training reminder fires: on the chosen [days] at [minuteOfDay] local time. Off by default and
 * deliberately gentle — one notification on a training day, none when a session was already saved that day.
 * Pure Kotlin (java.time), unit-tested.
 */
data class ReminderSchedule(val days: Set<DayOfWeek>, val minuteOfDay: Int) {
    init { require(minuteOfDay in 0 until 24 * 60) }

    val time: LocalTime get() = LocalTime.of(minuteOfDay / 60, minuteOfDay % 60)

    /** The next reminder strictly after [now], or null when no day is chosen. Handles DST via ZonedDateTime. */
    fun nextAfter(now: ZonedDateTime): ZonedDateTime? {
        if (days.isEmpty()) return null
        for (i in 0..7) {
            val date = now.toLocalDate().plusDays(i.toLong())
            if (date.dayOfWeek !in days) continue
            val at = ZonedDateTime.of(date, time, now.zone)
            if (at.isAfter(now)) return at
        }
        return null
    }

    /** "Mon, Wed, Fri at 18:00" / "Every day at 07:30". */
    fun describe(): String {
        val t = "%02d:%02d".format(minuteOfDay / 60, minuteOfDay % 60)
        val d = when {
            days.size == 7 -> "Every day"
            days.isEmpty() -> "No days chosen"
            days == WEEKDAYS -> "Weekdays"
            else -> DayOfWeek.entries.filter { it in days }.joinToString(", ") { SHORT[it.ordinal] }
        }
        return "$d at $t"
    }

    /** Stored as "1,3,5" (ISO day numbers, Monday = 1). */
    fun daysWire(): String = days.map { it.value }.sorted().joinToString(",")

    companion object {
        val SHORT = listOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        val WEEKDAYS = setOf(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY)
        val DEFAULT = ReminderSchedule(setOf(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY), 18 * 60)

        fun parseDays(wire: String?): Set<DayOfWeek>? = wire?.let { w ->
            w.split(',').mapNotNull { it.trim().toIntOrNull()?.takeIf { n -> n in 1..7 }?.let(DayOfWeek::of) }.toSet()
        }

        /** True when a session was saved on [now]'s local date: that day's reminder stays quiet. */
        fun trainedToday(sessionStarts: List<Long>, now: ZonedDateTime): Boolean {
            val today: LocalDate = now.toLocalDate()
            return sessionStarts.any { Instant.ofEpochMilli(it).atZone(now.zone).toLocalDate() == today }
        }

        /** The reminder's text: the plan's next session when one is being followed, otherwise a short open offer. */
        fun message(planName: String?, planNext: Int?, planTotal: Int?): String =
            if (planName != null && planNext != null && planTotal != null && planNext < planTotal) {
                "$planName: session ${planNext + 1} of $planTotal is ready when you are."
            } else {
                "A short session is ready when you are. Build one on Home in a few taps."
            }

        fun zone(): ZoneId = ZoneId.systemDefault()
    }
}
