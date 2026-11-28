package eu.motionforge.app.data

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.metadata.Device
import androidx.health.connect.client.records.metadata.Metadata
import eu.motionforge.app.feature.progress.HealthWorkout
import eu.motionforge.app.feature.progress.WorkoutKind
import java.time.Instant
import java.time.ZoneId

/**
 * Optional Health Connect export (Profile, off by default): each saved session becomes one exercise session record
 * (type, start and end time, title). Write only: the app never reads from Health Connect, and writes nothing else.
 * Every call fails quietly (returns false): a missing provider or a revoked permission must never break saving.
 */
class HealthConnectSync(private val context: Context) {
    enum class Availability { AVAILABLE, NEEDS_INSTALL_OR_UPDATE, UNAVAILABLE }

    fun availability(): Availability = runCatching {
        when (HealthConnectClient.getSdkStatus(context, PROVIDER)) {
            HealthConnectClient.SDK_AVAILABLE -> Availability.AVAILABLE
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> Availability.NEEDS_INSTALL_OR_UPDATE
            else -> Availability.UNAVAILABLE
        }
    }.getOrDefault(Availability.UNAVAILABLE)

    private fun client() = HealthConnectClient.getOrCreate(context, PROVIDER)

    suspend fun hasPermission(): Boolean = availability() == Availability.AVAILABLE && runCatching {
        client().permissionController.getGrantedPermissions().containsAll(PERMISSIONS)
    }.getOrDefault(false)

    /** Writes one workout; true when Health Connect accepted it. The record id is stable, so a retry is not a duplicate. */
    suspend fun write(w: HealthWorkout): Boolean {
        if (!hasPermission()) return false
        return runCatching {
            val zone = ZoneId.systemDefault()
            val start = Instant.ofEpochMilli(w.startMillis)
            val end = Instant.ofEpochMilli(w.endMillis)
            val record = ExerciseSessionRecord(
                startTime = start,
                startZoneOffset = zone.rules.getOffset(start),
                endTime = end,
                endZoneOffset = zone.rules.getOffset(end),
                metadata = Metadata.activelyRecorded(clientRecordId = w.clientId, device = Device(type = Device.TYPE_PHONE)),
                exerciseType = exerciseType(w.kind),
                title = w.title,
            )
            client().insertRecords(listOf(record))
            true
        }.getOrDefault(false)
    }

    companion object {
        const val PROVIDER = "com.google.android.apps.healthdata"
        val PERMISSIONS: Set<String> = setOf(HealthPermission.getWritePermission(ExerciseSessionRecord::class))

        fun exerciseType(k: WorkoutKind): Int = when (k) {
            WorkoutKind.BOXING -> ExerciseSessionRecord.EXERCISE_TYPE_BOXING
            WorkoutKind.HIIT -> ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING
            WorkoutKind.STRETCHING -> ExerciseSessionRecord.EXERCISE_TYPE_STRETCHING
            WorkoutKind.CALISTHENICS -> ExerciseSessionRecord.EXERCISE_TYPE_CALISTHENICS
        }
    }
}
