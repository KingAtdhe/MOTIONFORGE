package eu.motionforge.app.core.design

import android.provider.Settings
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import kotlinx.coroutines.delay

/** Frames per sprite written by tools/compose_studies.py. */
const val STUDY_FRAMES = 7

/** True when the phone's "remove animations" setting is on. */
@Composable
fun rememberReduceMotion(): Boolean {
    val context = LocalContext.current
    return remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
}

/**
 * A lesson's exposures played as a loop on the black plate: into the key position, a short hold, and back — the motion
 * study coming to life. With reduced motion, or until the frames have loaded, it shows the still study instead.
 */
@Composable
fun MotionFlipbook(framesPath: String, studyPath: String, modifier: Modifier = Modifier, description: String? = null) {
    val sprite = rememberArt(framesPath)
    val reduce = rememberReduceMotion()
    if (sprite == null || reduce) {
        MotionStudy(studyPath, modifier, description = description)
        return
    }
    var frame by remember(framesPath) { mutableIntStateOf(0) }
    LaunchedEffect(framesPath) {
        // forwards into the key position, hold, back to the start, hold
        val order = (0 until STUDY_FRAMES) + (STUDY_FRAMES - 2 downTo 1)
        while (true) {
            for (i in order) {
                frame = i
                delay(
                    when (i) {
                        STUDY_FRAMES - 1 -> 650L
                        0 -> 350L
                        else -> 110L
                    },
                )
            }
        }
    }
    Box(modifier.clip(PlateShape).background(MfColors.Plate).semantics { if (description != null) contentDescription = description }) {
        Canvas(Modifier.fillMaxSize()) {
            val fw = sprite.width / STUDY_FRAMES
            val fh = sprite.height
            val scale = minOf(size.width / fw, size.height / fh)
            val dw = (fw * scale).toInt(); val dh = (fh * scale).toInt()
            drawImage(
                sprite,
                srcOffset = IntOffset(frame * fw, 0),
                srcSize = IntSize(fw, fh),
                dstOffset = IntOffset(((size.width - dw) / 2).toInt(), ((size.height - dh) / 2).toInt()),
                dstSize = IntSize(dw, dh),
            )
        }
    }
}
