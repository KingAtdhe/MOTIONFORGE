package eu.motionforge.app.data

import android.database.sqlite.SQLiteDatabase
import eu.motionforge.app.core.model.TrainingCategory
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

/**
 * Updating the app must keep the training history: a version-1 database (before hold times) is opened by the current
 * app, which migrates it in place. Old rows keep their reps; their hold time is unknown (null).
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class SessionDatabaseMigrationTest {
    private val context = RuntimeEnvironment.getApplication()

    @Test
    fun versionOneHistorySurvivesTheUpdate() {
        val file = context.getDatabasePath("motionforge.db")
        file.parentFile?.mkdirs()
        file.delete()
        // the version-1 schema exactly as Room 2.7 created it
        SQLiteDatabase.openOrCreateDatabase(file, null).use { db ->
            db.execSQL(
                "CREATE TABLE IF NOT EXISTS `sessions` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `title` TEXT NOT NULL, " +
                    "`session_type` TEXT NOT NULL, `started_at` INTEGER NOT NULL, `completed_at` INTEGER NOT NULL, " +
                    "`duration_seconds` INTEGER NOT NULL, `perceived_effort` INTEGER, `completed` INTEGER NOT NULL)",
            )
            db.execSQL(
                "CREATE TABLE IF NOT EXISTS `session_exercises` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                    "`session_id` INTEGER NOT NULL, `exercise_id` TEXT NOT NULL, `name` TEXT NOT NULL, `sequence_number` INTEGER NOT NULL, " +
                    "`duration_seconds` INTEGER NOT NULL, `repetition_count` INTEGER, `tracking_quality` TEXT NOT NULL, " +
                    "FOREIGN KEY(`session_id`) REFERENCES `sessions`(`id`) ON UPDATE NO ACTION ON DELETE CASCADE )",
            )
            db.execSQL("CREATE INDEX IF NOT EXISTS `index_session_exercises_session_id` ON `session_exercises` (`session_id`)")
            db.execSQL("INSERT INTO sessions (id, title, session_type, started_at, completed_at, duration_seconds, perceived_effort, completed) " +
                "VALUES (1, 'Short fitness session', 'fitness', 1000, 2000, 95, 6, 1)")
            db.execSQL("INSERT INTO session_exercises (session_id, exercise_id, name, sequence_number, duration_seconds, repetition_count, tracking_quality) " +
                "VALUES (1, 'bodyweight_squat', 'Bodyweight Squat', 1, 60, 12, 'good')")
            db.version = 1
        }
        val history = runBlocking { SessionRepository(context).history.first() }
        assertEquals(1, history.size)
        val ex = history.single().exercises.single()
        assertEquals(TrainingCategory.FITNESS, history.single().type)
        assertEquals(12, ex.repetitions)
        assertNull(ex.heldSeconds)
    }
}
