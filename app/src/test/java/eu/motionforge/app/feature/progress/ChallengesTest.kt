package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZoneOffset
import org.junit.Test

class ChallengesTest {
    private val zone: ZoneId = ZoneOffset.UTC
    private val day0 = LocalDate.of(2026, 11, 2)   // a Monday
    private fun at(day: Int, hour: Int = 10) = day0.plusDays(day.toLong()).atTime(hour, 0).toInstant(ZoneOffset.UTC).toEpochMilli()
    private var nextId = 1L

    private fun session(
        day: Int, hour: Int = 10, seconds: Int = 600, type: TrainingCategory = TrainingCategory.FITNESS,
        vararg ex: ExerciseRecord,
    ) = SessionRecord(nextId++, "S", type, at(day, hour), seconds, null, true, ex.toList())

    private fun ex(id: String, reps: Int? = null, held: Int? = null) = ExerciseRecord(id, id, 60, reps, "ok", held)

    @Test
    fun encodeDecodeRoundTripsAndSkipsJunk() {
        val list = listOf(JoinedChallenge(Challenge.HABIT, 100L), JoinedChallenge(Challenge.SQUATS, 200L))
        assertEquals(list, Challenges.decode(Challenges.encode(list)))
        assertEquals(list, Challenges.decode("HABIT@100,NOPE@5,SQUATS@x,SQUATS@200,,@"))
        assertEquals(emptyList<JoinedChallenge>(), Challenges.decode(null))
        // one entry per challenge, the latest join wins
        assertEquals(listOf(JoinedChallenge(Challenge.HABIT, 300L)), Challenges.decode("HABIT@100,HABIT@300"))
    }

    @Test
    fun onlySessionsInsideTheWindowCount() {
        val j = JoinedChallenge(Challenge.HABIT, at(0, 9))
        val history = listOf(
            session(0, hour = 8),            // before joining: not counted
            session(0, hour = 12),
            session(5),
            session(27),                     // last day of 28
            session(28),                     // the day after the window: not counted
        )
        val p = Challenges.progress(j, history, day0.plusDays(30), zone)
        assertEquals(3, p.done)
        assertEquals(ChallengeStatus.ENDED, p.status)
        assertEquals(28, p.day)
        assertNull(p.completedAtMillis)
    }

    @Test
    fun runningShowsTheDayAndCompletesOnTheSessionThatReachesTheTarget() {
        val j = JoinedChallenge(Challenge.CARDIO, at(0, 0))
        val cardio = { d: Int -> session(d, 10, 600, TrainingCategory.FITNESS, ex("jumping_jack")) }
        val five = (0 until 5).map { cardio(it) } + session(5, 10, 600, TrainingCategory.FITNESS, ex("bodyweight_squat", reps = 10))
        val running = Challenges.progress(j, five, day0.plusDays(6), zone)
        assertEquals(5, running.done)
        assertEquals(7, running.day)
        assertEquals(ChallengeStatus.RUNNING, running.status)

        val sixth = cardio(8)
        val done = Challenges.progress(j, five + sixth, day0.plusDays(20), zone)
        assertEquals(ChallengeStatus.COMPLETE, done.status)     // complete stays complete after the window
        assertEquals(sixth.startedAtMillis, done.completedAtMillis)
        assertEquals(1f, done.fraction)
    }

    @Test
    fun repChallengesCountOnlyCameraCountedRepsOfTheirMove() {
        val j = JoinedChallenge(Challenge.SQUATS, at(0, 0))
        val history = listOf(
            session(1, ex = arrayOf(ex("bodyweight_squat", reps = 20), ex("push_up", reps = 10), ex("sumo_squat", reps = 15))),
            session(2, ex = arrayOf(ex("bodyweight_squat", reps = null), ex("dumbbell_goblet_squat", reps = 12))),
            session(3, ex = arrayOf(ex("jumping_jack"))),
        )
        assertEquals(47, Challenges.progress(j, history, day0.plusDays(3), zone).done)
        val pj = JoinedChallenge(Challenge.PUSH_UPS, at(0, 0))
        val pushes = listOf(session(1, ex = arrayOf(ex("push_up", reps = 10), ex("wall_push_up", reps = 8), ex("knee_push_up", reps = 5))))
        assertEquals(23, Challenges.progress(pj, pushes, day0.plusDays(3), zone).done)
    }

    @Test
    fun minutesHoldsFightingAndVariety() {
        val start = at(0, 0)
        val history = listOf(
            session(1, seconds = 30 * 60, type = TrainingCategory.FIGHTING_FUNDAMENTALS, ex = arrayOf(ex("boxing_jab"), ex("forearm_plank", held = 45))),
            session(2, seconds = 45 * 60 + 59, ex = arrayOf(ex("boxing_jab"), ex("bodyweight_squat"), ex("forearm_plank", held = 75))),
        )
        val today = day0.plusDays(3)
        assertEquals(75, Challenges.progress(JoinedChallenge(Challenge.HUNDRED_MINUTES, start), history, today, zone).done)
        assertEquals(120, Challenges.progress(JoinedChallenge(Challenge.STEADY, start), history, today, zone).done)
        assertEquals(1, Challenges.progress(JoinedChallenge(Challenge.RING_TIME, start), history, today, zone).done)
        assertEquals(3, Challenges.progress(JoinedChallenge(Challenge.EXPLORER, start), history, today, zone).done)
    }

    @Test
    fun atMostThreeRunAndRestartingKeepsOneEntry() {
        var joined = emptyList<JoinedChallenge>()
        for (c in listOf(Challenge.HABIT, Challenge.SQUATS, Challenge.LUNGES)) joined = Challenges.join(joined, c, at(0), emptyList(), zone)
        assertEquals(3, joined.size)
        // a fourth is refused while three run
        assertEquals(joined, Challenges.join(joined, Challenge.EXPLORER, at(1), emptyList(), zone))
        // restarting one that runs is allowed and replaces it
        val restarted = Challenges.join(joined, Challenge.SQUATS, at(2), emptyList(), zone)
        assertEquals(3, restarted.size)
        assertEquals(at(2), restarted.first { it.challenge == Challenge.SQUATS }.startedAtMillis)
        // an ended challenge frees its slot (the 2-week one ends first)
        val withShort = Challenges.join(Challenges.remove(joined, Challenge.LUNGES), Challenge.HUNDRED_MINUTES, at(0), emptyList(), zone)
        val later = Challenges.join(withShort, Challenge.EXPLORER, at(15), emptyList(), zone)
        assertTrue(later.any { it.challenge == Challenge.EXPLORER })
    }

    @Test
    fun newlyCompletedReportsOnlyTheSaveThatCrossedTheLine() {
        val now = System.currentTimeMillis()
        val joined = listOf(JoinedChallenge(Challenge.HABIT, now - 1000), JoinedChallenge(Challenge.EXPLORER, now - 1000))
        val local = ZoneId.systemDefault()
        fun s(i: Int, id: String) = SessionRecord(i.toLong(), "S", TrainingCategory.FITNESS, now - 900 + i, 600, null, true, listOf(ex(id)))
        val before = (1..11).map { s(it, "bodyweight_squat") }
        val after = before + s(12, "push_up")
        assertEquals(listOf(Challenge.HABIT), Challenges.newlyCompleted(joined, before, after, local))
        assertEquals(emptyList<Challenge>(), Challenges.newlyCompleted(joined, after, after + s(13, "lunge"), local))
    }
}
