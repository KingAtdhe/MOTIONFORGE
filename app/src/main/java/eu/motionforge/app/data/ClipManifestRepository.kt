package eu.motionforge.app.data

import android.content.Context
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.render3d.ClipManifest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/** Reads each coach's clip manifest (bundled asset) once and caches it. */
class ClipManifestRepository(context: Context) {
    private val appContext = context.applicationContext
    private val mutex = Mutex()
    private val cached = mutableMapOf<Coach, ClipManifest>()

    suspend fun trainer(coach: Coach = Coach.DEFAULT): Result<ClipManifest> = mutex.withLock {
        val existing = cached[coach]
        if (existing != null) {
            Result.success(existing)
        } else {
            withContext(Dispatchers.IO) {
                runCatching {
                    ClipManifest.parse(appContext.assets.open(coach.manifestPath).bufferedReader().use { it.readText() })
                }
            }.onSuccess { cached[coach] = it }
        }
    }
}
