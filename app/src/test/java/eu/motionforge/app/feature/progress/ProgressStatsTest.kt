package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

class ProgressStatsTest {
    private val zone = ZoneId.of("Europe/Belgrade")
    private val today = LocalDate.of(2026, 11, 18) // Wednesday
    private fun rec(date: String, seconds: Int) = SessionRecord(
        0, "s", TrainingCategory.FITNESS, LocalDateTime.parse(date).atZone(zone).toInstant().toEpochMilli(), seconds, null, true, emptyList(),
    )

    @Test
    fun emptyHistory() {
        val s = ProgressStats.summarize(emptyList(), today, zone)
        assertEquals(0, s.sessionsThisWeek); assertEquals(0, s.minutesThisWeek); assertEquals(4, s.recentWeeks.size)
    }

    @Test
    fun weekStartsOnMonday() {
        val s = ProgressStats.summarize(
            listOf(rec("2026-11-16T00:05:00", 300), rec("2026-11-18T10:00:00", 280), rec("2026-11-15T23:50:00", 600)), today, zone,
        )
        assertEquals(2, s.sessionsThisWeek)
        assertEquals(10, s.minutesThisWeek) // 580 s rounds to 10
        assertEquals(1, s.recentWeeks[2].sessions)
        assertEquals(LocalDate.of(2026, 11, 16), s.recentWeeks.last().weekStart)
        assertEquals(3, s.totalSessions)
    }

    @Test
    fun shortTrainingStillShowsOneMinute() {
        assertEquals(1, ProgressStats.summarize(listOf(rec("2026-11-18T10:00:00", 20)), today, zone).minutesThisWeek)
    }

    @Test
    fun oldSessionsOnlyCountInTotal() {
        val s = ProgressStats.summarize(listOf(rec("2026-08-01T10:00:00", 600)), today, zone)
        assertEquals(0, s.recentWeeks.sumOf { it.sessions }); assertEquals(1, s.totalSessions)
    }

    @Test
    fun trainedDaysOnlyCoverThisWeek() {
        val s = ProgressStats.summarize(
            listOf(rec("2026-11-16T07:00:00", 300), rec("2026-11-16T19:00:00", 300), rec("2026-11-18T10:00:00", 280), rec("2026-11-15T23:50:00", 600)),
            today,
            zone,
        )
        assertEquals(setOf(java.time.DayOfWeek.MONDAY, java.time.DayOfWeek.WEDNESDAY), s.trainedDaysThisWeek)
    }
}
