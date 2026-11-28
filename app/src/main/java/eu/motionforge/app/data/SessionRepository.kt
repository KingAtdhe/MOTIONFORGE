package eu.motionforge.app.data

import android.content.Context
import androidx.room.Room
import eu.motionforge.app.core.database.SessionDatabase
import eu.motionforge.app.core.database.SessionEntity
import eu.motionforge.app.core.database.SessionExerciseEntity
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.feature.progress.ExerciseRecord
import eu.motionforge.app.feature.progress.SessionRecord
import eu.motionforge.app.feature.session.SessionState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine

/** Training history stored on this phone only (Room). Nothing is uploaded. */
class SessionRepository(context: Context) {
    private val db by lazy {
        Room.databaseBuilder(context.applicationContext, SessionDatabase::class.java, "motionforge.db")
            .addMigrations(SessionDatabase.MIGRATION_1_2, SessionDatabase.MIGRATION_2_3)
            .build()
    }
    private val dao get() = db.sessionDao()

    val history: Flow<List<SessionRecord>> by lazy {
        combine(dao.sessions(), dao.exercises()) { sessions, exercises ->
            val bySession = exercises.groupBy { it.sessionId }
            sessions.map { s ->
                SessionRecord(
                    id = s.id,
                    title = s.title,
                    type = TrainingCategory.entries.firstOrNull { it.wireName == s.sessionType } ?: TrainingCategory.FITNESS,
                    startedAtMillis = s.startedAt,
                    durationSeconds = s.durationSeconds,
                    perceivedEffort = s.perceivedEffort,
                    completed = s.completed,
                    exercises = bySession[s.id].orEmpty().map {
                        ExerciseRecord(it.exerciseId, it.name, it.durationSeconds, it.repetitionCount, it.trackingQuality, it.heldSeconds, it.cleanReps, it.shallowReps)
                    },
                )
            }
        }
    }

    suspend fun save(state: SessionState, startedAtMillis: Long, completedAtMillis: Long, perceivedEffort: Int?) {
        require(state.isSaveable) { "Session is too short to save" }
        dao.insert(
            SessionEntity(
                title = state.plan.title,
                sessionType = state.plan.type.wireName,
                startedAt = startedAtMillis,
                completedAt = completedAtMillis,
                durationSeconds = state.workSeconds,
                perceivedEffort = perceivedEffort?.coerceIn(1, 10),
                completed = !state.endedEarly,
            ),
            state.results.map {
                SessionExerciseEntity(
                    sessionId = 0, exerciseId = it.exerciseId, name = it.name, sequenceNumber = it.sequence,
                    durationSeconds = it.elapsedSeconds, repetitionCount = it.repetitions, trackingQuality = it.trackingQuality.wireName,
                    heldSeconds = it.heldSeconds, cleanReps = it.cleanReps, shallowReps = it.shallowReps,
                )
            },
        )
    }

    suspend fun deleteAll() = dao.deleteAll()
}
