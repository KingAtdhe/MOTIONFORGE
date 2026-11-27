package eu.motionforge.app.feature.reminders

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.DayOfWeek.FRIDAY
import java.time.DayOfWeek.MONDAY
import java.time.DayOfWeek.WEDNESDAY
import java.time.ZoneId
import java.time.ZonedDateTime

class ReminderScheduleTest {
    private val zone = ZoneId.of("Europe/Berlin")
    private fun at(y: Int, mo: Int, d: Int, h: Int, mi: Int = 0) = ZonedDateTime.of(y, mo, d, h, mi, 0, 0, zone)
    private val mwf = ReminderSchedule(setOf(MONDAY, WEDNESDAY, FRIDAY), 18 * 60)

    @Test
    fun nextIsLaterTodayOrTheNextChosenDay() {
        // Wednesday 2026-11-25
        assertEquals(at(2026, 11, 25, 18), mwf.nextAfter(at(2026, 11, 25, 9)))
        assertEquals("exactly at the time → the next one", at(2026, 11, 27, 18), mwf.nextAfter(at(2026, 11, 25, 18)))
        assertEquals(at(2026, 11, 27, 18), mwf.nextAfter(at(2026, 11, 25, 19)))
        // Friday evening → Monday
        assertEquals(at(2026, 11, 30, 18), mwf.nextAfter(at(2026, 11, 27, 20)))
    }

    @Test
    fun oneDayAWeekWrapsToNextWeek() {
        val mon = ReminderSchedule(setOf(MONDAY), 7 * 60 + 30)
        assertEquals(at(2026, 12, 7, 7, 30), mon.nextAfter(at(2026, 11, 30, 8)))
    }

    @Test
    fun noDaysMeansNoReminder() = assertNull(ReminderSchedule(emptySet(), 600).nextAfter(at(2026, 11, 25, 9)))

    @Test
    fun keepsLocalTimeAcrossDaylightSaving() {
        // clocks go back on Sunday 2026-10-25 in Berlin: Monday's reminder is still 18:00 local
        val next = mwf.nextAfter(at(2026, 10, 24, 12))!!
        assertEquals(18, next.hour)
        assertEquals(26, next.dayOfMonth)
    }

    @Test
    fun quietOnADayAlreadyTrained() {
        val now = at(2026, 11, 25, 18)
        assertTrue(ReminderSchedule.trainedToday(listOf(at(2026, 11, 25, 7).toInstant().toEpochMilli()), now))
        assertFalse(ReminderSchedule.trainedToday(listOf(at(2026, 11, 24, 23, 50).toInstant().toEpochMilli()), now))
        assertFalse(ReminderSchedule.trainedToday(emptyList(), now))
    }

    @Test
    fun wireAndTextRoundTrip() {
        assertEquals("1,3,5", mwf.daysWire())
        assertEquals(mwf.days, ReminderSchedule.parseDays("5,1,3"))
        assertEquals(emptySet<Any>(), ReminderSchedule.parseDays("9,x"))
        assertNull(ReminderSchedule.parseDays(null))
        assertEquals("Mon, Wed, Fri at 18:00", mwf.describe())
        assertEquals("Weekdays at 07:05", ReminderSchedule(ReminderSchedule.WEEKDAYS, 7 * 60 + 5).describe())
    }

    @Test
    fun messageNamesThePlansNextSession() {
        assertEquals("Foundations: session 4 of 12 is ready when you are.", ReminderSchedule.message("Foundations", 3, 12))
        assertTrue(ReminderSchedule.message("Foundations", 12, 12).startsWith("A short session"))
        assertTrue(ReminderSchedule.message(null, null, null).startsWith("A short session"))
    }
}
