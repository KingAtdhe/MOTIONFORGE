package eu.motionforge.app.core.coaching

import android.content.Context
import android.media.AudioAttributes
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * Speaks coaching lines with the phone's own text-to-speech engine (on device; nothing is sent anywhere by the app).
 * If the phone has no usable engine or English voice, [available] stays false and [speak] does nothing:
 * the on-screen cues remain the source of truth.
 */
class CoachSpeaker(context: Context) {
    private var ready = false
    /** True when speaking in the app's (non-English) language. */
    private var translated = false
    private var tts: TextToSpeech? = null

    /** True once an English voice is ready to speak. */
    val available: Boolean get() = ready

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            val engine = tts ?: return@TextToSpeech
            if (status != TextToSpeech.SUCCESS) return@TextToSpeech
            // the app's language when the phone has a voice for it (then lines are spoken translated), else English
            val app = eu.motionforge.app.core.i18n.I18n.language
            val own = Locale.forLanguageTag(app).takeIf { app != "en" && engine.isLanguageAvailable(it) >= TextToSpeech.LANG_AVAILABLE }
            translated = own != null
            val lang = own ?: listOf(Locale.getDefault(), Locale.UK, Locale.US).firstOrNull { loc ->
                loc.language == "en" && engine.isLanguageAvailable(loc) >= TextToSpeech.LANG_AVAILABLE
            } ?: Locale.UK.takeIf { engine.isLanguageAvailable(it) >= TextToSpeech.LANG_AVAILABLE }
            if (lang == null || engine.setLanguage(lang) < TextToSpeech.LANG_AVAILABLE) return@TextToSpeech
            engine.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE) // spoken guidance over music
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build(),
            )
            engine.setSpeechRate(1.0f)
            ready = true
        }
    }

    fun speak(u: Utterance) {
        val engine = tts ?: return
        if (!ready) return
        engine.speak(if (translated) eu.motionforge.app.core.i18n.I18n.t(u.text) else u.text, if (u.interrupt) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD, null, "mf-${u.hashCode()}")
    }

    fun stop() {
        tts?.stop()
    }

    fun shutdown() {
        ready = false
        tts?.stop()
        tts?.shutdown()
        tts = null
    }
}
