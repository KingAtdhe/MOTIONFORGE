package eu.motionforge.app.feature.session

/**
 * Shadow-boxing rounds: what the coach calls out. Only moves taught in the lesson catalogue, at most three punches per
 * call, no kicks and nothing with a partner. Early rounds keep to single punches and the 1-2; later rounds add
 * defence and three-punch combinations. Pure Kotlin, unit-tested.
 */
object ShadowRounds {
    /** A call, the lesson that teaches it (calls are dropped when that lesson isn't in the catalogue) and its tier. */
    data class Call(val text: String, val lessonId: String, val tier: Int)

    val CALLS = listOf(
        Call("Jab", "boxing_jab", 1),
        Call("Double jab", "boxing_double_jab", 1),
        Call("One, two", "boxing_one_two", 1),
        Call("Jab to the body", "boxing_body_jab", 1),
        Call("Move your feet", "footwork_forward_backward", 1),
        Call("Lead hook", "boxing_lead_hook", 2),
        Call("Slip", "boxing_slip", 2),
        Call("Roll", "boxing_roll", 2),
        Call("Cross, hook", "boxing_cross_hook", 2),
        Call("Jab, slip", "boxing_jab_slip", 2),
        Call("Pull back, cross", "boxing_pull_counter", 2),
        Call("Uppercut, hook", "boxing_uppercut_hook", 2),
        Call("Circle left", "footwork_circle_left", 2),
        Call("One, one, two", "boxing_jab_jab_cross", 3),
        Call("One, two, three", "boxing_one_two_hook", 3),
        Call("Two, three, two", "boxing_cross_hook_cross", 3),
        Call("One, two, uppercut", "boxing_one_two_uppercut", 3),
        Call("Cover, cross", "boxing_block_cross", 3),
        Call("Roll, hook", "boxing_roll_hook", 3),
        Call("Circle right", "footwork_circle_right", 3),
    )

    /** The lesson the round is demonstrated with (light bounce in the stance; it carries the camera guard check). */
    const val ROUND_LESSON = "boxing_stance_bounce"
    const val CALL_EVERY_SECONDS = 6

    /**
     * Calls for round [round] (1-based): the tiers unlocked so far, in a stable order for the [seed], never the same
     * call twice in a row, enough for a [seconds]-long round.
     */
    fun callsFor(round: Int, seconds: Int, available: Set<String>, seed: Long): List<String> {
        val pool = CALLS.filter { it.tier <= round.coerceAtLeast(1) && it.lessonId in available }
        if (pool.isEmpty()) return emptyList()
        val n = ((seconds - SessionStep.Work.FIRST_CALL_SECOND) / CALL_EVERY_SECONDS + 1).coerceAtLeast(1)
        var s = seed * 6364136223846793005L + round * 1442695040888963407L
        val out = ArrayList<String>(n)
        while (out.size < n) {
            s = s * 6364136223846793005L + 1442695040888963407L
            val pick = pool[((s ushr 33) % pool.size).toInt()]
            // new tiers show up more often in their own round
            if (pick.tier < round && pool.any { it.tier == round } && ((s ushr 20) and 3L) == 0L) continue
            if (out.isNotEmpty() && out.last() == pick.text && pool.size > 1) continue
            out += pick.text
        }
        return out
    }
}
