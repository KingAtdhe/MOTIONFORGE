package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class HealthWorkoutTest {
    @Test
    fun kindFollowsWhatWasTrained() {
        assertEquals(WorkoutKind.BOXING, HealthWorkouts.kindOf(TrainingCategory.FIGHTING_FUNDAMENTALS, "build-rounds-10-n-20100-L1"))
        assertEquals(WorkoutKind.BOXING, HealthWorkouts.kindOf(TrainingCategory.FIGHTING_FUNDAMENTALS, "lesson-boxing_jab"))
        assertEquals(WorkoutKind.STRETCHING, HealthWorkouts.kindOf(TrainingCategory.FITNESS, "flow-morning"))
        assertEquals(WorkoutKind.STRETCHING, HealthWorkouts.kindOf(TrainingCategory.FITNESS, "build-stretch-10-n-20100-L1"))
        assertEquals(WorkoutKind.HIIT, HealthWorkouts.kindOf(TrainingCategory.FITNESS, "build-cardio-15-n-20100-L2"))
        assertEquals(WorkoutKind.CALISTHENICS, HealthWorkouts.kindOf(TrainingCategory.FITNESS, "quick"))
        assertEquals(WorkoutKind.CALISTHENICS, HealthWorkouts.kindOf(TrainingCategory.FITNESS, "build-legs-20-d-20100-L3"))
    }

    @Test
    fun aWorkoutHasAStableIdAndOnlyTimesTypeAndTitle() {
        val w = HealthWorkouts.of("Core, 10 min", TrainingCategory.FITNESS, "build-core-10-n-20100-L1", 1_000_000L, 1_600_000L)!!
        assertEquals("corza-session-1000000", w.clientId)
        assertEquals(HealthWorkouts.of("Core, 10 min", TrainingCategory.FITNESS, "build-core-10-n-20100-L1", 1_000_000L, 1_600_000L), w)
        assertEquals(WorkoutKind.CALISTHENICS, w.kind)
        assertEquals(1_000_000L, w.startMillis)
        assertEquals(1_600_000L, w.endMillis)
        assertNull("too short", HealthWorkouts.of("x", TrainingCategory.FITNESS, "quick", 0L, 5_000L))
        assertEquals(100, HealthWorkouts.of("y".repeat(300), TrainingCategory.FITNESS, "quick", 0L, 60_000L)!!.title.length)
    }
}
