package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.BoxingDrill
import eu.motionforge.app.data.ExerciseCatalogParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SessionBuilderTest {
    private val catalog = ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText())
    private val byId = catalog.associateBy { it.id }
    private val COOL_DOWN = setOf("standing_quad_stretch", "cross_body_shoulder_stretch", "kneeling_hip_flexor_stretch",
        "overhead_triceps_stretch", "chest_opener_stretch", "childs_pose")

    private fun build(f: SessionFocus, min: Int, db: Boolean = false, day: Long = 20_000, level: Int = 1) =
        SessionBuilder.build(catalog, SessionBuilder.Params(f, min, db, day, level))!!

    @Test
    fun everyFocusAndLengthBuildsAPlanCloseToItsLength() {
        for (level in SessionBuilder.LEVELS) for (f in SessionFocus.entries) for (m in SessionBuilder.MINUTES) {
            val p = build(f, m, level = level)
            val works = p.steps.filterIsInstance<SessionStep.Work>()
            assertTrue("$f $m: ${works.size} moves", works.size >= 2)
            assertTrue("$f $m lasts ${p.totalSeconds}", p.totalSeconds in (m * 60 - 120)..(m * 60 + 60))
            assertTrue("$f $m starts with a move", p.steps.first() is SessionStep.Work)
            if (f == SessionFocus.ROUNDS) continue // every round is the same shadow-boxing step (own test below)
            assertTrue("$f $m: a move back to back", works.zipWithNext().none { (a, b) -> a.exerciseId == b.exerciseId })
            // every move of the day's list comes before any repeat
            val main = works.map { it.exerciseId }.filter { it != "standing_mobility_warmup" }
                .let { ids -> if (f == SessionFocus.STRETCH) ids else ids.filter { it !in COOL_DOWN } }
            val distinct = main.distinct().size
            assertEquals("$f $m: repeats before the list is used", distinct, main.take(distinct).toSet().size)
            works.forEach { assertNotNull(it.exerciseId, byId[it.exerciseId]) }
        }
    }

    @Test
    fun equipmentOnlyWhenAskedFor() {
        for (f in SessionFocus.entries) for (m in SessionBuilder.MINUTES) {
            build(f, m).steps.filterIsInstance<SessionStep.Work>().forEach { assertTrue(it.exerciseId, !byId.getValue(it.exerciseId).needsEquipment) }
        }
        val upper = build(SessionFocus.UPPER, 20, db = true).steps.filterIsInstance<SessionStep.Work>()
        assertTrue("dumbbell moves appear", upper.any { byId.getValue(it.exerciseId).needsEquipment })
        upper.forEach { w -> byId.getValue(w.exerciseId).equipment.filter { "(" !in it }.forEach { assertTrue(it, it.startsWith("Dumbbell")) } }
    }

    @Test
    fun warmUpFirstAndCoolDownLast() {
        val p = build(SessionFocus.LEGS, 15).steps.filterIsInstance<SessionStep.Work>()
        assertEquals("standing_mobility_warmup", p.first().exerciseId)
        assertTrue(p.last().exerciseId.contains("stretch") || p.last().exerciseId == "childs_pose")
        val stretch = build(SessionFocus.STRETCH, 10).steps.filterIsInstance<SessionStep.Work>()
        assertTrue("no warm-up before stretching", stretch.none { it.exerciseId == "standing_mobility_warmup" })
    }

    @Test
    fun boxingStartsWithTheStanceAndNeverScoresFootwork() {
        val p = build(SessionFocus.BOXING, 10)
        assertEquals(TrainingCategory.FIGHTING_FUNDAMENTALS, p.type)
        val works = p.steps.filterIsInstance<SessionStep.Work>()
        assertEquals(SessionPlanner.STANCE_ID, works[1].exerciseId)
        assertTrue(works.none { it.exerciseId.startsWith("footwork_") })
    }

    @Test
    fun theSameDayGivesTheSameSessionAndAnotherDayAnother() {
        assertEquals(build(SessionFocus.CORE, 10, day = 5), build(SessionFocus.CORE, 10, day = 5))
        assertNotEquals(build(SessionFocus.CORE, 10, day = 5), build(SessionFocus.CORE, 10, day = 6))
    }

    @Test
    fun keysRoundTrip() {
        val k = SessionBuilder.key(SessionFocus.UPPER, 15, true, 20_123)
        assertEquals(SessionBuilder.Params(SessionFocus.UPPER, 15, true, 20_123), SessionBuilder.parseKey(k))
        assertNull(SessionBuilder.parseKey("build-upper-7-d-1"))
        assertNull(SessionBuilder.parseKey("quick"))
        assertNull(SessionBuilder.parseKey("build-nope-10-n-1"))
    }

    @Test
    fun roundsAreBelledCalledAndRested() {
        for (m in SessionBuilder.MINUTES) {
            val p = build(SessionFocus.ROUNDS, m)
            assertEquals(TrainingCategory.FIGHTING_FUNDAMENTALS, p.type)
            val rounds = p.steps.filterIsInstance<SessionStep.Work>().filter { it.round != null }
            assertTrue("$m min: ${rounds.size} rounds", rounds.size >= 2)
            assertEquals((1..rounds.size).toList(), rounds.map { it.round })
            rounds.forEach { r ->
                assertEquals(SessionBuilder.roundSeconds(m), r.durationSeconds)
                assertEquals(ShadowRounds.ROUND_LESSON, r.exerciseId)
                assertEquals("the guard check runs in rounds", BoxingDrill.STANCE, r.formDrill)
                assertTrue(r.calls.isNotEmpty())
                assertTrue("no call twice in a row", r.calls.zipWithNext().none { (a, b) -> a == b })
            }
            // 45 s between rounds
            p.steps.zipWithNext().filter { (a, b) -> a is SessionStep.Rest && (b as? SessionStep.Work)?.round?.let { it > 1 } == true }
                .forEach { (a, _) -> assertEquals(SessionBuilder.roundRest(1), a.durationSeconds) }
        }
    }

    @Test
    fun roundCallsOnlyUseTaughtMovesAndBuildUp() {
        val ids = byId.keys
        ShadowRounds.CALLS.forEach { assertTrue("${it.text}: ${it.lessonId} missing", it.lessonId in ids) }
        val first = ShadowRounds.callsFor(1, 120, ids, 7).toSet()
        val tier1 = ShadowRounds.CALLS.filter { it.tier == 1 }.map { it.text }.toSet()
        assertTrue("round 1 keeps to singles and the 1-2: $first", tier1.containsAll(first))
        val third = ShadowRounds.callsFor(3, 120, ids, 7)
        assertTrue("round 3 adds three-punch combinations", third.any { c -> ShadowRounds.CALLS.first { it.text == c }.tier == 3 })
        assertEquals(ShadowRounds.callsFor(2, 120, ids, 7), ShadowRounds.callsFor(2, 120, ids, 7))
        // nothing beyond three punches is ever called
        ShadowRounds.CALLS.forEach { assertTrue(it.text, it.text.split(',').size <= 3) }
    }

    @Test
    fun levelsFollowRecentTrainingAndEaseBackAfterABreak() {
        val day = 24L * 60 * 60 * 1000
        val now = 1_000L * day
        assertEquals(1, SessionBuilder.levelFor(emptyList(), now))
        assertEquals(1, SessionBuilder.levelFor(List(3) { now - it * day }, now))
        assertEquals(2, SessionBuilder.levelFor(List(4) { now - it * day }, now))
        assertEquals(3, SessionBuilder.levelFor(List(10) { now - it * 3 * day }, now))
        // ten sessions, all more than six weeks ago: back to level 1
        assertEquals(1, SessionBuilder.levelFor(List(10) { now - (43 + it) * day }, now))
    }

    @Test
    fun higherLevelsHaveLongerMovesAndHarderVariants() {
        val l1 = build(SessionFocus.UPPER, 20, level = 1).steps.filterIsInstance<SessionStep.Work>()
        val l3 = build(SessionFocus.UPPER, 20, level = 3).steps.filterIsInstance<SessionStep.Work>()
        val main1 = l1.filter { it.exerciseId != "standing_mobility_warmup" && it.durationSeconds != 45 }
        val main3 = l3.filter { it.exerciseId != "standing_mobility_warmup" && it.durationSeconds != 45 }
        assertTrue(main1.all { it.durationSeconds == 40 })
        assertTrue(main3.all { it.durationSeconds == 50 })
        assertTrue("no full push-ups at level 1", l1.none { it.exerciseId == "push_up" })
        assertTrue("full push-ups at level 3", l3.any { it.exerciseId == "push_up" })
        assertTrue("no wall or knee push-ups at level 3", l3.none { it.exerciseId == "wall_push_up" || it.exerciseId == "knee_push_up" })
        // boxing rounds rest less at higher levels
        val rests = build(SessionFocus.ROUNDS, 15, level = 3).steps.zipWithNext()
            .filter { (a, b) -> a is SessionStep.Rest && (b as? SessionStep.Work)?.round?.let { it > 1 } == true }
        assertTrue(rests.isNotEmpty() && rests.all { (a, _) -> a.durationSeconds == SessionBuilder.roundRest(3) })
    }

    @Test
    fun levelIsPartOfTheKeyAndOldKeysStillRead() {
        val k = SessionBuilder.key(SessionFocus.CORE, 10, false, 20_100, level = 3)
        assertEquals(SessionBuilder.Params(SessionFocus.CORE, 10, false, 20_100, 3), SessionBuilder.parseKey(k))
        assertEquals(SessionBuilder.Params(SessionFocus.CORE, 10, false, 20_100, 1), SessionBuilder.parseKey("build-core-10-n-20100"))
        assertNull(SessionBuilder.parseKey("build-core-10-n-20100-L9"))
    }
}
