package eu.motionforge.app.data

import android.content.Context
import eu.motionforge.app.core.model.Exercise
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Offline catalogue backed by the JSON file bundled in app assets. */
class ExerciseRepository(private val context: Context) {

    suspend fun loadCatalog(): Result<List<Exercise>> = withContext(Dispatchers.IO) {
        runCatching {
            val text = context.assets.open(ExerciseCatalogParser.ASSET_PATH).bufferedReader().use { it.readText() }
            ExerciseCatalogParser.parse(text)
        }
    }
}
