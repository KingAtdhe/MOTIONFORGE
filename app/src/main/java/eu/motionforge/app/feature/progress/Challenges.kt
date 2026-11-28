package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.CountedMove
import eu.motionforge.app.feature.session.SessionFocus
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.temporal.ChronoUnit

/** What a challenge counts. Everything is measured from saved sessions: nothing is self-reported or estimated. */
enum class ChallengeMeasure { SESSIONS, MINUTES, SQUATS, PUSH_UPS, LUNGES, FIGHTING_SESSIONS, CARDIO_SESSIONS, HOLD_SECONDS, EXERCISES }

/**
 * An opt-in challenge over a fixed window that starts when the person joins it. Calm by design, like the weekly goal:
 * no reminders, no countdown warnings; if the window ends first the challenge simply ends and can be started again.
 * Rep and hold challenges count only what the camera counted or timed, so a guided (uncounted) lesson never adds to them.
 */
enum class Challenge(val title: String, val detail: String, val days: Int, val target: Int, val measure: ChallengeMeasure, val mark: String) {
    HABIT("Four-week habit", "Save 12 sessions in 4 weeks.", 28, 12, ChallengeMeasure.SESSIONS, "12"),
    HUNDRED_MINUTES("Hundred minutes", "Train for 100 minutes in 2 weeks.", 14, 100, ChallengeMeasure.MINUTES, "100′"),
    SQUATS("300 squats", "300 squats counted by the camera in 4 weeks. Every squat lesson the camera counts adds to it.", 28, 300, ChallengeMeasure.SQUATS, "300"),
    PUSH_UPS("150 push-ups", "150 push-ups counted by the camera in 4 weeks. Wall, incline and knee push-ups count too.", 28, 150, ChallengeMeasure.PUSH_UPS, "150"),
    LUNGES("200 lunges", "200 lunges counted by the camera in 4 weeks. Every lunge lesson the camera counts adds to it.", 28, 200, ChallengeMeasure.LUNGES, "200"),
    RING_TIME("Ring time", "Save 8 fighting fundamentals sessions in 4 weeks.", 28, 8, ChallengeMeasure.FIGHTING_SESSIONS, "8"),
    CARDIO("Cardio fortnight", "Save 6 sessions with cardio moves in 2 weeks.", 14, 6, ChallengeMeasure.CARDIO_SESSIONS, "6"),
    STEADY("Ten steady minutes", "Hold positions for 10 minutes in total in 3 weeks, timed by the camera.", 21, 600, ChallengeMeasure.HOLD_SECONDS, "10′"),
    EXPLORER("Explorer", "Try 20 different exercises in 4 weeks.", 28, 20, ChallengeMeasure.EXERCISES, "20"),
}

/** A challenge the person joined, and when. */
data class JoinedChallenge(val challenge: Challenge, val startedAtMillis: Long)

enum class ChallengeStatus { RUNNING, COMPLETE, ENDED }

data class ChallengeProgress(
    val joined: JoinedChallenge,
    /** Amount so far in the challenge's own unit (minutes for MINUTES, seconds for HOLD_SECONDS). */
    val done: Int,
    /** Day of the window, 1-based, never past the last day. */
    val day: Int,
    val status: ChallengeStatus,
    /** When the session that completed it started; null unless complete. */
    val completedAtMillis: Long?,
) {
    val challenge: Challenge get() = joined.challenge
    val fraction: Float get() = (done.toFloat() / challenge.target).coerceIn(0f, 1f)
}

object Challenges {
    /** Challenges that can run at the same time. */
    const val MAX_RUNNING = 3

    private val cardioIds: Set<String> by lazy { SessionFocus.CARDIO.ids.toSet() }

    fun encode(list: List<JoinedChallenge>): String = list.joinToString(",") { "${it.challenge.name}@${it.startedAtMillis}" }

    /** Tolerant: unknown names and broken entries are skipped; one entry per challenge (the latest wins). */
    fun decode(wire: String?): List<JoinedChallenge> {
        if (wire.isNullOrBlank()) return emptyList()
        val parsed = wire.split(",").mapNotNull { part ->
            val name = part.substringBefore("@", "")
            val at = part.substringAfter("@", "").toLongOrNull()
            val c = Challenge.entries.firstOrNull { it.name == name }
            if (c != null && at != null && at > 0) JoinedChallenge(c, at) else null
        }
        return parsed.groupBy { it.challenge }.map { (_, v) -> v.maxBy { it.startedAtMillis } }.sortedBy { it.startedAtMillis }
    }

    fun startDate(j: JoinedChallenge, zone: ZoneId): LocalDate = Instant.ofEpochMilli(j.startedAtMillis).atZone(zone).toLocalDate()

    /** First day after the window (exclusive end). */
    fun endDate(j: JoinedChallenge, zone: ZoneId): LocalDate = startDate(j, zone).plusDays(j.challenge.days.toLong())

    private fun inWindow(j: JoinedChallenge, r: SessionRecord, zone: ZoneId): Boolean =
        r.startedAtMillis >= j.startedAtMillis &&
            Instant.ofEpochMilli(r.startedAtMillis).atZone(zone).toLocalDate() < endDate(j, zone)

    private fun reps(r: SessionRecord, vararg moves: CountedMove): Int =
        r.exercises.filter { CountedMove.forExercise(it.exerciseId) in moves }.sumOf { it.repetitions ?: 0 }

    /** Replays the sessions in the window oldest first; returns the running total after each, in raw units. */
    private fun runningTotals(c: Challenge, sessions: List<SessionRecord>): List<Pair<SessionRecord, Int>> {
        val seen = HashSet<String>()
        var total = 0
        return sessions.map { r ->
            total += when (c.measure) {
                ChallengeMeasure.SESSIONS -> 1
                ChallengeMeasure.MINUTES -> r.durationSeconds
                ChallengeMeasure.SQUATS -> reps(r, CountedMove.SQUAT)
                ChallengeMeasure.PUSH_UPS -> reps(r, CountedMove.PUSH_UP, CountedMove.WALL_PUSH_UP)
                ChallengeMeasure.LUNGES -> reps(r, CountedMove.LUNGE)
                ChallengeMeasure.FIGHTING_SESSIONS -> if (r.type == TrainingCategory.FIGHTING_FUNDAMENTALS) 1 else 0
                ChallengeMeasure.CARDIO_SESSIONS -> if (r.exercises.any { it.exerciseId in cardioIds }) 1 else 0
                ChallengeMeasure.HOLD_SECONDS -> r.exercises.sumOf { it.heldSeconds ?: 0 }
                ChallengeMeasure.EXERCISES -> {
                    val before = seen.size
                    seen.addAll(r.exercises.map { it.exerciseId })
                    seen.size - before
                }
            }
            r to total
        }
    }

    private fun toUnit(c: Challenge, raw: Int): Int = if (c.measure == ChallengeMeasure.MINUTES) raw / 60 else raw

    fun progress(j: JoinedChallenge, records: List<SessionRecord>, today: LocalDate, zone: ZoneId): ChallengeProgress {
        val c = j.challenge
        val totals = runningTotals(c, records.filter { inWindow(j, it, zone) }.sortedBy { it.startedAtMillis })
        val done = toUnit(c, totals.lastOrNull()?.second ?: 0)
        val completedAt = totals.firstOrNull { toUnit(c, it.second) >= c.target }?.first?.startedAtMillis
        val day = (ChronoUnit.DAYS.between(startDate(j, zone), today) + 1).toInt().coerceIn(1, c.days)
        val status = when {
            completedAt != null -> ChallengeStatus.COMPLETE
            !today.isBefore(endDate(j, zone)) -> ChallengeStatus.ENDED
            else -> ChallengeStatus.RUNNING
        }
        return ChallengeProgress(j, done, day, status, completedAt)
    }

    fun all(joined: List<JoinedChallenge>, records: List<SessionRecord>, today: LocalDate, zone: ZoneId): List<ChallengeProgress> =
        joined.map { progress(it, records, today, zone) }

    fun runningCount(joined: List<JoinedChallenge>, records: List<SessionRecord>, today: LocalDate, zone: ZoneId): Int =
        all(joined, records, today, zone).count { it.status == ChallengeStatus.RUNNING }

    /**
     * Join [c] now (or start it again from now if it was joined before). Refused (returns [joined] unchanged) when
     * [MAX_RUNNING] other challenges are already running.
     */
    fun join(joined: List<JoinedChallenge>, c: Challenge, nowMillis: Long, records: List<SessionRecord>, zone: ZoneId): List<JoinedChallenge> {
        val others = joined.filter { it.challenge != c }
        val today = Instant.ofEpochMilli(nowMillis).atZone(zone).toLocalDate()
        if (runningCount(others, records, today, zone) >= MAX_RUNNING) return joined
        return others + JoinedChallenge(c, nowMillis)
    }

    fun remove(joined: List<JoinedChallenge>, c: Challenge): List<JoinedChallenge> = joined.filter { it.challenge != c }

    /** Challenges that the newest save completed: complete after it, not before. */
    fun newlyCompleted(joined: List<JoinedChallenge>, before: List<SessionRecord>, after: List<SessionRecord>, zone: ZoneId): List<Challenge> {
        val today = LocalDate.now(zone)
        val was = all(joined, before, today, zone).filter { it.status == ChallengeStatus.COMPLETE }.map { it.challenge }.toSet()
        return all(joined, after, today, zone).filter { it.status == ChallengeStatus.COMPLETE && it.challenge !in was }.map { it.challenge }
    }
}
