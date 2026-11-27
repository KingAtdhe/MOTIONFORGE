package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.temporal.TemporalAdjusters

/**
 * Weekly goal and streak. Calm by design (product spec: no pressure-based streaks): the streak counts *weeks* in a
 * row in which the person reached their own weekly goal, so rest days never break it, and a week that is still running
 * never breaks it either — the streak only ends once a whole week has passed below the goal. No warnings, no guilt.
 */
data class WeekStreak(
    /** Weeks in a row with the goal reached, ending this week if it is already reached, else last week. */
    val current: Int,
    /** The longest such run ever. */
    val best: Int,
    /** Sessions saved this week (Mon–Sun). */
    val doneThisWeek: Int,
    val goal: Int,
) {
    val metThisWeek: Boolean get() = doneThisWeek >= goal
    val toGo: Int get() = (goal - doneThisWeek).coerceAtLeast(0)
}

/** A badge: earned once, kept for good. [atMillis] = when the session that earned it started. */
data class EarnedBadge(val badge: Badge, val atMillis: Long)

/** Achievements are plain milestones of training done; none rewards training through pain or every single day. */
/** [mark] = the short sign on the medal (numbers and symbols only, the same in every language). */
enum class Badge(val title: String, val detail: String, val mark: String) {
    FIRST_SESSION("First session", "Saved your first session.", "1"),
    FIRST_ROUNDS("First rounds", "Finished a fighting fundamentals session.", "1·2"),
    ALL_ROUNDER("All-rounder", "Trained both fitness and fighting fundamentals.", "+"),
    TEN_SESSIONS("Ten sessions", "Saved 10 sessions.", "10"),
    TWENTY_FIVE("25 sessions", "Saved 25 sessions.", "25"),
    FIFTY("50 sessions", "Saved 50 sessions.", "50"),
    FIRST_HOUR("First hour", "Trained for 60 minutes in total.", "60′"),
    FIVE_HOURS("Five hours", "Trained for 5 hours in total.", "300′"),
    HUNDRED_REPS("100 reps", "100 reps counted by the camera.", "100"),
    THOUSAND_REPS("1,000 reps", "1,000 reps counted by the camera.", "1000"),
    STEADY("Steady", "Held positions for 5 minutes in total, timed by the camera.", "5′"),
    PERSONAL_BEST("Personal best", "Beat your own rep count on an exercise.", "↑"),
    GOAL_WEEK("Goal reached", "Reached your weekly goal.", "✓"),
    FOUR_WEEKS("Four weeks", "Reached your weekly goal 4 weeks in a row.", "4×"),
    TWELVE_WEEKS("Twelve weeks", "Reached your weekly goal 12 weeks in a row.", "12×"),
}

object Milestones {
    const val DEFAULT_GOAL = 3
    val GOAL_RANGE = 1..7

    fun weekOf(millis: Long, zone: ZoneId): LocalDate =
        Instant.ofEpochMilli(millis).atZone(zone).toLocalDate().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))

    fun streak(records: List<SessionRecord>, today: LocalDate, zone: ZoneId, goal: Int): WeekStreak {
        val g = goal.coerceIn(GOAL_RANGE)
        val thisWeek = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
        val perWeek = records.groupingBy { weekOf(it.startedAtMillis, zone) }.eachCount()
        val done = perWeek[thisWeek] ?: 0
        fun met(w: LocalDate) = (perWeek[w] ?: 0) >= g
        var w = if (done >= g) thisWeek else thisWeek.minusWeeks(1)
        var current = 0
        while (met(w)) { current++; w = w.minusWeeks(1) }
        var best = 0
        var run = 0
        var prev: LocalDate? = null
        for (wk in perWeek.keys.filter { met(it) && it <= thisWeek }.sorted()) {
            run = if (prev != null && wk == prev.plusWeeks(1)) run + 1 else 1
            best = maxOf(best, run)
            prev = wk
        }
        return WeekStreak(current, maxOf(best, current), done, g)
    }

    /**
     * Every badge earned so far, in the order they were earned, replaying the history oldest first: a badge's time is
     * the session that first made it true. Weekly-goal badges use the goal as it is set now.
     */
    fun badges(records: List<SessionRecord>, zone: ZoneId, goal: Int): List<EarnedBadge> {
        val g = goal.coerceIn(GOAL_RANGE)
        val sorted = records.sortedBy { it.startedAtMillis }
        val earned = LinkedHashMap<Badge, Long>()
        var sessions = 0
        var seconds = 0L
        var reps = 0
        var held = 0
        var fighting = false
        var fitness = false
        val bestReps = HashMap<String, Int>()
        val perWeek = HashMap<LocalDate, Int>()
        var bestRun = 0
        fun earn(b: Badge, at: Long, cond: Boolean) { if (cond && b !in earned) earned[b] = at }
        for (r in sorted) {
            val at = r.startedAtMillis
            sessions++
            seconds += r.durationSeconds
            if (r.type == TrainingCategory.FIGHTING_FUNDAMENTALS) fighting = true else fitness = true
            var beat = false
            for (e in r.exercises) {
                e.repetitions?.let { n ->
                    reps += n
                    val before = bestReps[e.exerciseId]
                    if (before != null && n > before) beat = true
                    if (before == null || n > before) bestReps[e.exerciseId] = n
                }
                held += e.heldSeconds ?: 0
            }
            val wk = weekOf(at, zone)
            perWeek[wk] = (perWeek[wk] ?: 0) + 1
            var run = 0
            var w = wk
            while ((perWeek[w] ?: 0) >= g) { run++; w = w.minusWeeks(1) }
            bestRun = maxOf(bestRun, run)

            earn(Badge.FIRST_SESSION, at, true)
            earn(Badge.FIRST_ROUNDS, at, r.type == TrainingCategory.FIGHTING_FUNDAMENTALS && r.completed)
            earn(Badge.ALL_ROUNDER, at, fighting && fitness)
            earn(Badge.TEN_SESSIONS, at, sessions >= 10)
            earn(Badge.TWENTY_FIVE, at, sessions >= 25)
            earn(Badge.FIFTY, at, sessions >= 50)
            earn(Badge.FIRST_HOUR, at, seconds >= 60 * 60)
            earn(Badge.FIVE_HOURS, at, seconds >= 5 * 60 * 60)
            earn(Badge.HUNDRED_REPS, at, reps >= 100)
            earn(Badge.THOUSAND_REPS, at, reps >= 1000)
            earn(Badge.STEADY, at, held >= 5 * 60)
            earn(Badge.PERSONAL_BEST, at, beat)
            earn(Badge.GOAL_WEEK, at, bestRun >= 1)
            earn(Badge.FOUR_WEEKS, at, bestRun >= 4)
            earn(Badge.TWELVE_WEEKS, at, bestRun >= 12)
        }
        return earned.map { (b, t) -> EarnedBadge(b, t) }
    }

    /** Badges [after] has that [before] didn't: what a just-saved session earned. */
    fun newlyEarned(before: List<SessionRecord>, after: List<SessionRecord>, zone: ZoneId, goal: Int): List<Badge> {
        val had = badges(before, zone, goal).map { it.badge }.toSet()
        return badges(after, zone, goal).map { it.badge }.filter { it !in had }
    }
}
