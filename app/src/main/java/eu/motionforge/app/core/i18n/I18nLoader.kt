package eu.motionforge.app.core.i18n

import android.content.Context
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive

/** Loads a language's table from assets/i18n/<lang>.json (a flat object: English source -> translation). */
object I18nLoader {
    fun apply(context: Context, lang: String) {
        if (lang == "en") { I18n.use("en", emptyMap()); return }
        val entries = runCatching {
            val text = context.assets.open("i18n/$lang.json").bufferedReader().use { it.readText() }
            (Json.parseToJsonElement(text) as JsonObject).mapValues { it.value.jsonPrimitive.content }
        }.getOrElse { emptyMap() }
        I18n.use(if (entries.isEmpty()) "en" else lang, entries)
    }
}
