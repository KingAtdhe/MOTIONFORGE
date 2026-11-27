package eu.motionforge.app.core.i18n

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** Every language table covers the extracted source strings with the same placeholders and line breaks. */
class I18nTablesTest {
    private val source = (Json.parseToJsonElement(File("../tools/i18n/source.json").readText()) as JsonArray).map { it.jsonPrimitive.content }
    private val ph = Regex("\\{\\d+\\}")

    @Test
    fun everyEuLanguageHasACompleteTable() {
        val langs = I18n.CODES - "en"
        assertEquals(23, langs.size)
        for (lang in langs) {
            val f = File("src/main/assets/i18n/$lang.json")
            assertTrue("$lang table", f.exists())
            val t = (Json.parseToJsonElement(f.readText()) as JsonObject).mapValues { it.value.jsonPrimitive.content }
            val missing = source.filter { t[it].isNullOrBlank() }
            assertTrue("$lang missing ${missing.take(3)}", missing.isEmpty())
            t.forEach { (k, v) ->
                assertEquals("$lang placeholders: $k", ph.findAll(k).map { it.value }.sorted().toList(), ph.findAll(v).map { it.value }.sorted().toList())
                assertEquals("$lang line breaks: $k", k.count { it == '\n' }, v.count { it == '\n' })
            }
        }
    }

    @Test
    fun aLessonReadsInAnotherLanguage() {
        val t = (Json.parseToJsonElement(File("src/main/assets/i18n/de.json").readText()) as JsonObject).mapValues { it.value.jsonPrimitive.content }
        I18n.use("de", t)
        try {
            assertTrue(I18n.t("Round 2 of 4") != "Round 2 of 4")
            assertTrue(I18n.t("Bodyweight Squat") != "Bodyweight Squat")
        } finally {
            I18n.use("en", emptyMap())
        }
    }
}
