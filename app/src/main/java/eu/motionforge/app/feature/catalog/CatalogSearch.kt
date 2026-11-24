package eu.motionforge.app.feature.catalog

import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import java.text.Normalizer

/**
 * Text search over the lesson catalogue. Every word typed must match the lesson somewhere (name, purpose, equipment,
 * cues, instructions, category) or through one of the everyday words in [SYNONYMS] ("abs", "legs", "punch"…).
 * Results are ordered by how well they match: name starts with the query, then name contains it, then the rest;
 * ties keep catalogue order.
 */
object CatalogSearch {

    /** Everyday words people type, mapped to words that appear in the lessons. */
    private val SYNONYMS: Map<String, List<String>> = mapOf(
        "abs" to listOf("crunch", "plank", "core", "dead bug", "mountain climber", "twist", "hollow", "sit-up", "leg raise"),
        "core" to listOf("crunch", "plank", "dead bug", "bird dog", "twist", "hollow"),
        "stomach" to listOf("crunch", "plank", "core"),
        "belly" to listOf("crunch", "plank", "core"),
        "leg" to listOf("squat", "lunge", "calf", "deadlift", "bridge", "step-up", "wall sit"),
        "thigh" to listOf("squat", "lunge"),
        "quad" to listOf("squat", "lunge"),
        "glute" to listOf("bridge", "squat", "lunge", "deadlift", "kickback"),
        "butt" to listOf("glute", "bridge", "squat", "lunge"),
        "bum" to listOf("glute", "bridge", "squat", "lunge"),
        "hamstring" to listOf("deadlift", "hinge", "bridge", "good morning"),
        "calves" to listOf("calf"),
        "arm" to listOf("biceps", "hammer curl", "triceps", "push-up", "dip"),
        "bicep" to listOf("biceps", "hammer curl"),
        "biceps" to listOf("biceps", "hammer curl"),
        "tricep" to listOf("triceps", "dip", "push-up"),
        "chest" to listOf("push-up", "press", "fly"),
        "pec" to listOf("push-up", "press", "fly"),
        "shoulder" to listOf("press", "raise", "circle", "pull-apart", "fly"),
        "back" to listOf("row", "superman", "reverse fly", "pull-apart", "bird dog", "hinge", "deadlift"),
        "cardio" to listOf("jack", "march", "high knee", "mountain climber", "footwork", "shuffle", "skater", "shadow"),
        "warm" to listOf("warm-up", "mobility", "circle", "march"),
        "warmup" to listOf("warm-up", "mobility"),
        "stretch" to listOf("mobility", "cat-cow", "stretch"),
        "punch" to listOf("jab", "cross", "hook", "uppercut", "one-two", "combination"),
        "punches" to listOf("jab", "cross", "hook", "uppercut"),
        "strike" to listOf("jab", "cross", "hook", "uppercut"),
        "boxing" to listOf("fighting", "jab", "cross", "hook", "uppercut", "guard", "stance", "footwork", "slip", "roll"),
        "fight" to listOf("fighting"),
        "combo" to listOf("combination", "one-two", "jab-jab", "cross-hook", "1-2"),
        "defence" to listOf("defense", "slip", "roll", "block", "parry", "pull back", "guard", "catch"),
        "defense" to listOf("defence", "slip", "roll", "block", "parry", "pull back", "guard", "catch"),
        "dodge" to listOf("slip", "roll", "pull back", "duck"),
        "feet" to listOf("footwork", "step", "pivot", "calf"),
        "dumbbell" to listOf("dumbbells"),
        "weight" to listOf("dumbbell", "kettlebell"),
        "weights" to listOf("dumbbell", "kettlebell"),
        "kb" to listOf("kettlebell"),
        "db" to listOf("dumbbell"),
        "band" to listOf("resistance band"),
        "floor" to listOf("mat"),
        "pushup" to listOf("push-up"),
        "pushups" to listOf("push-up"),
        "situp" to listOf("sit-up", "crunch"),
    )

    /** Words that only ever mean boxing: their everyday matches are looked for in fighting lessons only ("cross" is
     *  also how a curtsy lunge's leg moves). */
    private val FIGHT_WORDS = setOf("punch", "punches", "strike", "boxing", "fight", "combo", "defence", "defense", "dodge")

    fun normalize(s: String): String =
        Normalizer.normalize(s.lowercase(), Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .replace('–', '-').replace('—', '-')
            .replace(Regex("\\s+"), " ")
            .trim()

    /** Words of the query, without filler, each with simple singular/plural forms. */
    private fun terms(query: String): List<List<String>> =
        normalize(query).split(' ', ',', '/').filter { it.isNotBlank() && it !in FILLER }.map { w ->
            buildList {
                add(w)
                if (w.length > 3 && w.endsWith("es")) add(w.dropLast(2))
                if (w.length > 3 && w.endsWith("s")) add(w.dropLast(1))
                // "push up" written apart or together still finds "push-up"
                if (w.contains('-')) add(w.replace("-", ""))
            }
        }

    private val FILLER = setOf("the", "a", "an", "and", "for", "with", "my", "of", "to", "exercise", "exercises", "workout")

    /** Name, purpose, equipment and kind: what a lesson is. */
    private fun primary(e: Exercise): String = squash(
        buildString {
            append(e.name).append(' ')
            append(e.id.replace('_', ' ')).append(' ')
            append(e.purpose).append(' ')
            e.equipment.forEach { append(it).append(' ') }
            append(if (e.category == TrainingCategory.FIGHTING_FUNDAMENTALS) "fighting boxing" else e.category.displayName)
        },
    )

    /** Cues and steps: searched only for words without an everyday mapping ("back" is in "step back" everywhere). */
    private fun secondary(e: Exercise): String = squash((e.commonCues + e.instructions).joinToString(" "))

    /** The text plus a copy with hyphens dropped, so "pushup" finds "push-up". */
    private fun squash(text: String): String = normalize(text).let { it + " " + it.replace("-", "") }

    /** [term] at the start of a word ("jab" finds "jabbing", "arm" does not find "warm"). */
    private fun String.hasWord(term: String): Boolean {
        var i = indexOf(term)
        while (i >= 0) {
            if (i == 0 || !this[i - 1].isLetterOrDigit()) return true
            i = indexOf(term, i + 1)
        }
        return false
    }

    private fun matchesTerm(primary: String, secondary: String, forms: List<String>, fighting: Boolean = true): Boolean = forms.any { f ->
        val syn = if (!fighting && f in FIGHT_WORDS) emptyList() else SYNONYMS[f]
        primary.hasWord(f) || syn.orEmpty().any { primary.hasWord(normalize(it)) } || (SYNONYMS[f] == null && secondary.hasWord(f))
    }

    /** The lessons that match [query], best first. A blank query returns [exercises] unchanged. */
    fun search(exercises: List<Exercise>, query: String): List<Exercise> {
        val words = terms(query)
        if (words.isEmpty()) return exercises
        val q = normalize(query)
        // "push up" typed apart still finds "push-up"
        val joined = q.replace(" ", "").replace("-", "")
        // first what the lessons are (name, purpose, equipment); only if nothing matches, also their steps and cues
        val strict = matches(exercises, words, joined, q, withSteps = false)
        return strict.ifEmpty { matches(exercises, words, joined, q, withSteps = true) }
    }

    private fun matches(exercises: List<Exercise>, words: List<List<String>>, joined: String, q: String, withSteps: Boolean): List<Exercise> =
        exercises.mapIndexedNotNull { i, e ->
            val p = primary(e)
            val sec = if (withSteps) secondary(e) else ""
            val fighting = e.category == TrainingCategory.FIGHTING_FUNDAMENTALS
            val hit = words.all { matchesTerm(p, sec, it, fighting) } || (words.size > 1 && p.hasWord(joined))
            if (!hit) return@mapIndexedNotNull null
            val name = normalize(e.name)
            // a one-word query ranks by any of its forms, so "squats" orders the list exactly like "squat"
            val qs = if (words.size == 1) words[0] else listOf(q)
            val rank = when {
                qs.any { name.startsWith(it) } -> 0
                qs.any { name.contains(it) } || name.replace("-", "").contains(q.replace(" ", "").replace("-", "")) -> 1
                words.all { forms -> forms.any { name.contains(it) } } -> 2
                else -> 3
            }
            Triple(e, rank, i)
        }.sortedWith(compareBy({ it.second }, { it.third })).map { it.first }
}
