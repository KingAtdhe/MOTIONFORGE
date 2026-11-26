package eu.motionforge.app.core.database

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

/** Local training history. Mirrors database/schema.sql so optional cloud sync can map 1:1 later. */
@Entity(tableName = "sessions")
data class SessionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    @ColumnInfo(name = "session_type") val sessionType: String,
    @ColumnInfo(name = "started_at") val startedAt: Long,
    @ColumnInfo(name = "completed_at") val completedAt: Long,
    @ColumnInfo(name = "duration_seconds") val durationSeconds: Int,
    @ColumnInfo(name = "perceived_effort") val perceivedEffort: Int?,
    val completed: Boolean,
)

@Entity(
    tableName = "session_exercises",
    foreignKeys = [ForeignKey(entity = SessionEntity::class, parentColumns = ["id"], childColumns = ["session_id"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("session_id")],
)
data class SessionExerciseEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: Long,
    @ColumnInfo(name = "exercise_id") val exerciseId: String,
    val name: String,
    @ColumnInfo(name = "sequence_number") val sequenceNumber: Int,
    @ColumnInfo(name = "duration_seconds") val durationSeconds: Int,
    @ColumnInfo(name = "repetition_count") val repetitionCount: Int?,
    @ColumnInfo(name = "tracking_quality") val trackingQuality: String,
    /** Seconds held in position (hold checks), null when not measured. Added in version 2. */
    @ColumnInfo(name = "held_seconds") val heldSeconds: Int? = null,
)

@Dao
abstract class SessionDao {
    @Insert
    protected abstract suspend fun insertSession(session: SessionEntity): Long

    @Insert
    protected abstract suspend fun insertExercises(exercises: List<SessionExerciseEntity>)

    @Transaction
    open suspend fun insert(session: SessionEntity, exercises: List<SessionExerciseEntity>): Long {
        val id = insertSession(session)
        insertExercises(exercises.map { it.copy(sessionId = id) })
        return id
    }

    @Query("SELECT * FROM sessions ORDER BY started_at DESC")
    abstract fun sessions(): Flow<List<SessionEntity>>

    @Query("SELECT * FROM session_exercises ORDER BY session_id, sequence_number")
    abstract fun exercises(): Flow<List<SessionExerciseEntity>>

    @Query("DELETE FROM sessions")
    abstract suspend fun deleteAll()
}

@Database(entities = [SessionEntity::class, SessionExerciseEntity::class], version = 2, exportSchema = false)
abstract class SessionDatabase : RoomDatabase() {
    abstract fun sessionDao(): SessionDao

    companion object {
        /** 1 → 2: hold time per exercise (nullable, old rows stay null). Never a destructive migration: history is kept. */
        val MIGRATION_1_2 = object : androidx.room.migration.Migration(1, 2) {
            override fun migrate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE session_exercises ADD COLUMN held_seconds INTEGER")
            }
        }
    }
}
