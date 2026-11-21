package eu.motionforge.app.core.coaching

/** How important a spoken line is. Higher may cut off a lower one that is still being spoken. */
enum class CuePriority { INFO, PRAISE, COUNT, CORRECTION, ANNOUNCE }

/** A line for the text-to-speech engine. [interrupt] = stop whatever is being said first. */
data class Utterance(val text: String, val interrupt: Boolean)

/**
 * Decides which coaching lines are actually spoken, so the voice stays helpful instead of chatty.
 * Pure Kotlin (no Android types) so it is unit-tested.
 *
 * Rules:
 * - Nothing is said within [minGapMs] of the previous line, unless the new line has a higher priority
 *   (a correction may cut off praise; a step announcement may cut off anything).
 * - The same text is not repeated within [repeatGapMs] (counts are exempt: "Four." follows "Three.").
 * - Praise is rationed to one line per [praiseGapMs], so it keeps its meaning.
 */
class VoiceCoach(
    private val minGapMs: Long = 2_500,
    private val repeatGapMs: Long = 12_000,
    private val praiseGapMs: Long = 8_000,
) {
    private var lastAt = Long.MIN_VALUE / 2
    private var lastPriority = CuePriority.INFO
    private var lastPraiseAt = Long.MIN_VALUE / 2
    private val lastByText = HashMap<String, Long>()

    fun reset() {
        lastAt = Long.MIN_VALUE / 2
        lastPraiseAt = Long.MIN_VALUE / 2
        lastPriority = CuePriority.INFO
        lastByText.clear()
    }

    /** Returns the utterance to speak now, or null when the line should be dropped. */
    fun offer(text: String, priority: CuePriority, nowMs: Long): Utterance? {
        if (text.isBlank()) return null
        val sinceLast = nowMs - lastAt
        val outranks = priority > lastPriority
        if (sinceLast < minGapMs && !outranks) return null
        if (priority != CuePriority.COUNT && priority != CuePriority.ANNOUNCE) {
            val prev = lastByText[text]
            if (prev != null && nowMs - prev < repeatGapMs) return null
        }
        if (priority == CuePriority.PRAISE && nowMs - lastPraiseAt < praiseGapMs) return null

        lastAt = nowMs
        lastPriority = priority
        lastByText[text] = nowMs
        if (priority == CuePriority.PRAISE) lastPraiseAt = nowMs
        return Utterance(text, interrupt = outranks && sinceLast < minGapMs)
    }

    companion object {
        private val NUMBER_WORDS = listOf(
            "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty",
        )

        /** Spoken count ("Four."); numerals above twenty are left to the speech engine. */
        fun count(n: Int): String = (NUMBER_WORDS.getOrNull(n) ?: n.toString()) + "."

        private val PRAISE = listOf("Good.", "Nice and controlled.", "That's it.", "Good rep.")

        /** Rotating short praise so it does not sound like a loop. */
        fun praise(n: Int): String = PRAISE[Math.floorMod(n, PRAISE.size)]
    }
}
