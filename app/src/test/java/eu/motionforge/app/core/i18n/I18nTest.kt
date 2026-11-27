package eu.motionforge.app.core.i18n

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Locale

class I18nTest {
    private val de = mapOf(
        "Rest" to "Pause",
        "Round {0} of {1}" to "Runde {0} von {1}",
        "Next: {0}" to "Als Nächstes: {0}",
        "Jab" to "Jab",
        "Squat" to "Kniebeuge",
        "Chest tall." to "Brust aufrecht.",
        "Knees soft." to "Knie locker.",
        "{0} of {1} done" to "{1} gesamt, {0} erledigt",
    )

    @After fun back() = I18n.use("en", emptyMap())

    @Test
    fun englishIsTheSourceAndNeedsNoTable() {
        I18n.use("en", emptyMap())
        assertEquals("Round 2 of 4", I18n.t("Round 2 of 4"))
    }

    @Test
    fun exactTemplateAndSentenceMatching() {
        I18n.use("de", de)
        assertEquals("Pause", I18n.t("Rest"))
        assertEquals("Runde 2 von 4", I18n.t("Round 2 of 4"))
        // a placeholder that is itself translatable text is translated too
        assertEquals("Als Nächstes: Kniebeuge", I18n.t("Next: Squat"))
        // longer text: sentence by sentence; unknown sentences stay English
        assertEquals("Brust aufrecht. Knie locker. Breathe out.", I18n.t("Chest tall. Knees soft. Breathe out."))
        assertEquals("Brust aufrecht.\nKnie locker.", I18n.t("Chest tall.\nKnees soft."))
        // placeholders may change order
        assertEquals("5 gesamt, 3 erledigt", I18n.t("3 of 5 done"))
        assertEquals("Nothing known", I18n.t("Nothing known"))
        assertEquals("Runde 3 von 5", I18n.f("Round {0} of {1}", 3, 5))
    }

    @Test
    fun choosingALanguage() {
        assertEquals("de", I18n.resolve("", Locale.GERMANY))
        assertEquals("en", I18n.resolve("", Locale.JAPAN))
        assertEquals("fr", I18n.resolve("fr", Locale.GERMANY))
        assertEquals("de", I18n.resolve("xx", Locale.GERMANY))
        assertEquals(24, I18n.LANGUAGES.size)
    }
}
