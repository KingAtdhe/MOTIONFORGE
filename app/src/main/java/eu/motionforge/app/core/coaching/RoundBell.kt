package eu.motionforge.app.core.coaching

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool
import eu.motionforge.app.R

/** The bell at the start and end of a shadow-boxing round (a short sound bundled with the app, played on device). */
class RoundBell(context: Context) {
    private val pool = SoundPool.Builder()
        .setMaxStreams(1)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()
    private var loaded = false
    private val sound = pool.load(context.applicationContext, R.raw.round_bell, 1)

    init {
        pool.setOnLoadCompleteListener { _, id, status -> if (id == sound && status == 0) loaded = true }
    }

    fun ring() {
        if (loaded) pool.play(sound, 1f, 1f, 1, 0, 1f)
    }

    fun release() = pool.release()
}
