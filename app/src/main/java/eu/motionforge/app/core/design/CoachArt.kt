package eu.motionforge.app.core.design

import android.content.Context
import android.graphics.BitmapFactory
import android.util.LruCache
import androidx.compose.foundation.Image
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private object ArtCache {
    // ~10 MB of decoded stills is plenty for one screen of cards plus the hero
    val bitmaps = object : LruCache<String, ImageBitmap>(10 * 1024 * 1024) {
        override fun sizeOf(key: String, value: ImageBitmap) = value.width * value.height * 4
    }

    suspend fun load(context: Context, path: String): ImageBitmap? {
        bitmaps.get(path)?.let { return it }
        return withContext(Dispatchers.IO) {
            runCatching { context.assets.open(path).use { BitmapFactory.decodeStream(it) }?.asImageBitmap() }.getOrNull()
        }?.also { bitmaps.put(path, it) }
    }
}

/**
 * A rendered still of the coach from app assets. Decorative unless [contentDescription] is given.
 * Draws nothing while loading or if the asset is missing, so layouts never show a broken image.
 */
@Composable
fun CoachArt(
    path: String,
    modifier: Modifier = Modifier,
    contentDescription: String? = null,
    contentScale: ContentScale = ContentScale.Fit,
) {
    val context = LocalContext.current
    val bitmap by produceState(ArtCache.bitmaps.get(path), path) { value = ArtCache.load(context, path) }
    bitmap?.let { Image(it, contentDescription, modifier, contentScale = contentScale) }
}
