package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

class MilestonesTest {
    private val zone = ZoneId.of("Europe/Belgrade")
    private val today = LocalDate.of(2026, 11, 18) // Wednesday; week starts Mon 16 Nov

    private fun rec(
        date: String, seconds: Int = 600, type: TrainingCategory = TrainingCategory.FITNESS,
        exercises: List<ExerciseRecord> = emptyList(), completed: Boolean = true,
    ) = SessionRecord(0, "s", type, LocalDateTime.parse(date).atZone(zone).toInstant().toEpochMilli(), seconds, null, completed, exercises)

    /** [n] sessions in the week starting [monday]. */
    private fun week(monday: String, n: Int) = (0 until n).map { rec("${LocalDate.parse(monday).plusDays(it.toLong())}T18:00:00") }

    @Test
    fun noHistoryNoStreak() {
        val s = Milestones.streak(emptyList(), today, zone, 3)
        assertEquals(0, s.current); assertEquals(0, s.best); assertEquals(3, s.toGo); assertFalse(s.metThisWeek)
    }

    @Test
    fun runningWeekBelowGoalDoesNotBreakTheStreak() {
        // three earlier weeks at goal, this week only one session so far
        val h = week("2026-10-26", 3) + week("2026-11-02", 3) + week("2026-11-09", 3) + week("2026-11-16", 1)
        val s = Milestones.streak(h, today, zone, 3)
        assertEquals(3, s.current); assertEquals(1, s.doneThisWeek); assertEquals(2, s.toGo)
    }

    @Test
    fun reachingTheGoalThisWeekExtendsIt() {
        val h = week("2026-11-09", 2) + week("2026-11-16", 2)
        val s = Milestones.streak(h, today, zone, 2)
        assertEquals(2, s.current); assertTrue(s.metThisWeek)
    }

    @Test
    fun aWholeWeekBelowGoalEndsItButBestIsKept() {
        val h = week("2026-10-12", 2) + week("2026-10-19", 2) + week("2026-10-26", 2) + week("2026-11-02", 1) + week("2026-11-09", 2)
        val s = Milestones.streak(h, today, zone, 2)
        assertEquals(1, s.current); assertEquals(3, s.best)
    }

    @Test
    fun restDaysInsideAWeekDontMatter() {
        // goal 2: Monday and Sunday of each week, nothing in between
        val h = listOf(rec("2026-11-02T08:00:00"), rec("2026-11-08T20:00:00"), rec("2026-11-09T08:00:00"), rec("2026-11-15T20:00:00"))
        assertEquals(2, Milestones.streak(h, today, zone, 2).current)
    }

    @Test
    fun goalIsClamped() {
        assertEquals(7, Milestones.streak(emptyList(), today, zone, 40).goal)
        assertEquals(1, Milestones.streak(emptyList(), today, zone, 0).goal)
    }

    @Test
    fun badgesInOrderWithTheSessionThatEarnedThem() {
        val sq = { n: Int -> listOf(ExerciseRecord("squat", "Squat", 60, n, "good")) }
        val h = listOf(
            rec("2026-11-02T08:00:00", exercises = sq(40)),
            rec("2026-11-03T08:00:00", exercises = sq(45), type = TrainingCategory.FIGHTING_FUNDAMENTALS),
            rec("2026-11-04T08:00:00", exercises = sq(30)),
        )
        val b = Milestones.badges(h, zone, 3)
        val names = b.map { it.badge }
        assertEquals(Badge.FIRST_SESSION, names.first())
        assertTrue(Badge.FIRST_ROUNDS in names && Badge.ALL_ROUNDER in names && Badge.PERSONAL_BEST in names)
        assertTrue(Badge.HUNDRED_REPS in names) // 40 + 45 + 30
        assertTrue(Badge.GOAL_WEEK in names)
        assertEquals(h[1].startedAtMillis, b.first { it.badge == Badge.PERSONAL_BEST }.atMillis)
        assertEquals(h[2].startedAtMillis, b.first { it.badge == Badge.HUNDRED_REPS }.atMillis)
        assertFalse(Badge.TEN_SESSIONS in names)
    }

    @Test
    fun endedEarlyBoxingIsNotFirstRounds() {
        val names = Milestones.badges(listOf(rec("2026-11-02T08:00:00", type = TrainingCategory.FIGHTING_FUNDAMENTALS, completed = false)), zone, 3).map { it.badge }
        assertFalse(Badge.FIRST_ROUNDS in names)
    }

    @Test
    fun fourWeekBadgeNeedsFourGoalWeeksInARow() {
        val three = week("2026-10-19", 2) + week("2026-10-26", 2) + week("2026-11-02", 2)
        assertFalse(Badge.FOUR_WEEKS in Milestones.badges(three, zone, 2).map { it.badge })
        val four = three + week("2026-11-09", 2)
        assertTrue(Badge.FOUR_WEEKS in Milestones.badges(four, zone, 2).map { it.badge })
    }

    @Test
    fun newlyEarnedIsOnlyTheDifference() {
        val before = listOf(rec("2026-11-02T08:00:00"))
        val after = before + rec("2026-11-03T08:00:00", type = TrainingCategory.FIGHTING_FUNDAMENTALS)
        assertEquals(listOf(Badge.FIRST_ROUNDS, Badge.ALL_ROUNDER), Milestones.newlyEarned(before, after, zone, 3))
    }

    @Test
    fun holdsAndMinutesAddUp() {
        val hold = listOf(ExerciseRecord("plank", "Plank", 60, null, "good", heldSeconds = 100))
        val h = (0 until 3).map { rec("2026-11-0${it + 2}T08:00:00", seconds = 1300, exercises = hold) }
        val names = Milestones.badges(h, zone, 3).map { it.badge }
        assertTrue(Badge.STEADY in names)       // 300 s held
        assertTrue(Badge.FIRST_HOUR in names)   // 3900 s
    }
}
