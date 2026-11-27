package eu.motionforge.app.core.i18n

import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * Translation at the edge: the app's text stays English in code and in the lesson catalogue, and is translated where
 * it is shown (the app's [Text], spoken cues, notifications). A language is a table from English source strings to
 * translations; strings built from parts are matched as templates ("Round {0} of {1}"), and longer text that doesn't
 * match as a whole is translated sentence by sentence. Anything without a translation stays English.
 * Pure Kotlin, unit-tested; the tables are loaded from assets by [I18nLoader].
 */
object I18n {
    /** The EU's 24 official languages (ISO 639-1). English is the source. */
    val LANGUAGES: List<Pair<String, String>> = listOf(
        "bg" to "Български", "cs" to "Čeština", "da" to "Dansk", "de" to "Deutsch", "el" to "Ελληνικά", "en" to "English",
        "es" to "Español", "et" to "Eesti", "fi" to "Suomi", "fr" to "Français", "ga" to "Gaeilge", "hr" to "Hrvatski",
        "hu" to "Magyar", "it" to "Italiano", "lt" to "Lietuvių", "lv" to "Latviešu", "mt" to "Malti", "nl" to "Nederlands",
        "pl" to "Polski", "pt" to "Português", "ro" to "Română", "sk" to "Slovenčina", "sl" to "Slovenščina", "sv" to "Svenska",
    )
    val CODES: Set<String> = LANGUAGES.map { it.first }.toSet()

    @Volatile var language: String = "en"
        private set
    @Volatile private var table: Table = Table.EMPTY
    private val cache = ConcurrentHashMap<String, String>()

    /** The language to use for a stored choice ("" = the phone's language when it is one of ours, else English). */
    fun resolve(choice: String?, phone: Locale = Locale.getDefault()): String =
        choice?.takeIf { it in CODES } ?: phone.language.takeIf { it in CODES } ?: "en"

    fun use(lang: String, entries: Map<String, String>) {
        table = if (lang == "en") Table.EMPTY else Table(entries)
        language = lang
        cache.clear()
    }

    /** [en] in the current language (English when there is no translation). */
    fun t(en: String): String {
        if (en.isEmpty() || table === Table.EMPTY) return en
        return cache.getOrPut(en) { table.translate(en) }
    }

    /** A source template with {0}, {1}… filled in (the template is translated, then filled). */
    fun f(template: String, vararg args: Any?): String {
        var s = t(template)
        args.forEachIndexed { i, a -> s = s.replace("{$i}", a.toString()) }
        return s
    }

    class Table(entries: Map<String, String>) {
        private val exact = HashMap<String, String>()
        private val templates = ArrayList<Pair<Regex, String>>()

        init {
            for ((k, v) in entries) {
                if (v.isBlank()) continue
                if (PLACEHOLDER.containsMatchIn(k)) {
                    val parts = k.split(PLACEHOLDER)
                    val names = PLACEHOLDER.findAll(k).map { it.value }.toList()
                    val rx = buildString {
                        append('^')
                        parts.forEachIndexed { i, p ->
                            append(Regex.escape(p))
                            if (i < names.size) append("(.+?)")
                        }
                        append('$')
                    }
                    templates += Regex(rx) to translateOrder(names, v)
                } else exact[k] = v
            }
            // longer, more specific templates first
            templates.sortByDescending { it.first.pattern.length }
        }

        /** The translation with placeholders renumbered in the order they appear in the source. */
        private fun translateOrder(names: List<String>, v: String): String {
            var out = v
            names.forEachIndexed { i, n -> out = out.replace(n, "\u0000$i\u0000") }
            return out
        }

        fun translate(en: String): String {
            exact[en]?.let { return it }
            matchTemplate(en)?.let { return it }
            // sentence by sentence (lines, then sentences), keeping the separators
            if ('\n' in en) return en.split('\n').joinToString("\n") { translate(it) }
            val sentences = SENTENCE.split(en)
            if (sentences.size > 1) {
                val seps = SENTENCE.findAll(en).map { it.value }.toList()
                return buildString {
                    sentences.forEachIndexed { i, s ->
                        append(if (s.isEmpty()) s else exact[s] ?: matchTemplate(s) ?: s)
                        if (i < seps.size) append(seps[i])
                    }
                }
            }
            return en
        }

        private fun matchTemplate(en: String): String? {
            for ((rx, v) in templates) {
                val m = rx.matchEntire(en) ?: continue
                var out = v
                m.groupValues.drop(1).forEachIndexed { i, g ->
                    out = out.replace("\u0000$i\u0000", exact[g] ?: g)
                }
                return out
            }
            return null
        }

        companion object {
            val PLACEHOLDER = Regex("\\{\\d+\\}")
            /** Between sentences: after . ! ? or a colon, before the next sentence. */
            val SENTENCE = Regex("(?<=[.!?:])\\s+(?=\\S)")
            val EMPTY = Table(emptyMap())
        }
    }
}

/** Shorthand for [I18n.t]. */
fun tr(en: String): String = I18n.t(en)
