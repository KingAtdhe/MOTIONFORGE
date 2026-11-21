package eu.motionforge.app.core.coaching

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceCoachTest {

    @Test
    fun linesTooCloseTogetherAreDropped() {
        val v = VoiceCoach()
        assertNotNull(v.offer("Squats. 60 seconds.", CuePriority.ANNOUNCE, 0))
        assertNull(v.offer("Move at a controlled pace.", CuePriority.INFO, 1_000))
        assertNotNull(v.offer("Move at a controlled pace.", CuePriority.INFO, 3_000))
    }

    @Test
    fun aCorrectionCutsOffPraise() {
        val v = VoiceCoach()
        v.offer("Good jab.", CuePriority.PRAISE, 0)
        val u = v.offer("Keep the rear hand up.", CuePriority.CORRECTION, 500)
        assertEquals(Utterance("Keep the rear hand up.", interrupt = true), u)
    }

    @Test
    fun theSameCorrectionIsNotRepeatedStraightAway() {
        val v = VoiceCoach()
        assertNotNull(v.offer("Hands up by your face.", CuePriority.CORRECTION, 0))
        assertNull(v.offer("Hands up by your face.", CuePriority.CORRECTION, 5_000))
        assertNotNull(v.offer("Hands up by your face.", CuePriority.CORRECTION, 13_000))
    }

    @Test
    fun countsAreNeverTreatedAsRepeats() {
        val v = VoiceCoach()
        assertNotNull(v.offer("Ten seconds left.", CuePriority.COUNT, 0))
        assertNotNull(v.offer("Ten seconds left.", CuePriority.COUNT, 3_000))
    }

    @Test
    fun praiseIsRationed() {
        val v = VoiceCoach()
        assertNotNull(v.offer("Good jab.", CuePriority.PRAISE, 0))
        assertNull(v.offer("Good stance. Hands up, feet balanced.", CuePriority.PRAISE, 4_000))
        assertNotNull(v.offer("Good stance. Hands up, feet balanced.", CuePriority.PRAISE, 9_000))
    }

    @Test
    fun spokenNumbers() {
        assertEquals("Four.", VoiceCoach.count(4))
        assertEquals("25.", VoiceCoach.count(25))
        assertTrue(VoiceCoach.praise(-1).isNotBlank())
    }
}
