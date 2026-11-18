package eu.motionforge.app.data

import android.content.Context
import eu.motionforge.app.core.render3d.ClipManifest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/** Reads the trainer's clip manifest (bundled asset) once and caches it. */
class ClipManifestRepository(context: Context) {
    private val appContext = context.applicationContext
    private val mutex = Mutex()
    private var cached: ClipManifest? = null

    suspend fun trainer(): Result<ClipManifest> = mutex.withLock {
        val existing = cached
        if (existing != null) {
            Result.success(existing)
        } else {
            withContext(Dispatchers.IO) {
                runCatching {
                    ClipManifest.parse(appContext.assets.open(ClipManifest.TRAINER_MANIFEST_PATH).bufferedReader().use { it.readText() })
                }
            }.onSuccess { cached = it }
        }
    }
}
