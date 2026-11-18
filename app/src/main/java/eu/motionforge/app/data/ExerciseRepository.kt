package eu.motionforge.app.data

import android.content.Context
import eu.motionforge.app.core.model.Exercise
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/** Offline catalogue backed by the JSON file bundled in app assets. Parsed once, then cached. */
class ExerciseRepository(context: Context) {

    private val appContext = context.applicationContext
    private val mutex = Mutex()
    private var cached: List<Exercise>? = null

    suspend fun loadCatalog(): Result<List<Exercise>> = mutex.withLock {
        val existing = cached
        if (existing != null) {
            Result.success(existing)
        } else {
            withContext(Dispatchers.IO) {
                runCatching {
                    val text = appContext.assets.open(ExerciseCatalogParser.ASSET_PATH).bufferedReader().use { it.readText() }
                    ExerciseCatalogParser.parse(text)
                }
            }.onSuccess { cached = it }
        }
    }
}
