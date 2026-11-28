package eu.motionforge.app.feature.progress

import eu.motionforge.app.core.model.TrainingCategory

/** What kind of workout a session is, for Health Connect's exercise type (mapped in data/HealthConnectSync). */
enum class WorkoutKind { BOXING, HIIT, STRETCHING, CALISTHENICS }

/**
 * A saved session as it is written to Health Connect: an exercise session with a type, start and end time and title,
 * and nothing else (no calories, no heart rate, nothing estimated). [clientId] is stable for the session, so a retry
 * never writes it twice.
 */
data class HealthWorkout(val clientId: String, val title: String, val kind: WorkoutKind, val startMillis: Long, val endMillis: Long)

object HealthWorkouts {
    /** Sessions shorter than this are not worth a workout entry (the app does not save them either). */
    const val MIN_SECONDS = 10

    fun kindOf(category: TrainingCategory, planKey: String): WorkoutKind = when {
        category == TrainingCategory.FIGHTING_FUNDAMENTALS -> WorkoutKind.BOXING
        planKey.startsWith("flow-") || planKey.startsWith("build-stretch-") -> WorkoutKind.STRETCHING
        planKey.startsWith("build-cardio-") -> WorkoutKind.HIIT
        else -> WorkoutKind.CALISTHENICS
    }

    fun of(title: String, category: TrainingCategory, planKey: String, startMillis: Long, endMillis: Long): HealthWorkout? {
        if (endMillis - startMillis < MIN_SECONDS * 1000L) return null
        return HealthWorkout("corza-session-$startMillis", title.take(100), kindOf(category, planKey), startMillis, endMillis)
    }
}
