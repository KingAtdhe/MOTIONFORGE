package eu.motionforge.app.data

import eu.motionforge.app.core.model.AnalysisMode
import eu.motionforge.app.core.model.CameraView
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.Level
import eu.motionforge.app.core.model.TrainingCategory
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull

/**
 * Parses the bundled exercise catalogue. Parsing is strict on purpose: an unknown field,
 * category, view or analysis mode is a content error and must fail loudly in tests, not
 * silently fall back to a mode that could enable feedback that has not been validated.
 *
 * Uses the JSON tree API (no code generation), so it needs no compiler plugin.
 */
object ExerciseCatalogParser {

    /** Location of the bundled catalogue inside app assets. */
    const val ASSET_PATH = "exercise_data/exercises.json"

    private val knownKeys = setOf(
        "id", "name", "category", "level", "durationSeconds", "recommendedView", "analysisMode",
        "demoAnimation", "safety", "instructions", "commonCues", "limitations",
    )

    fun parse(text: String): List<Exercise> {
        val root = try {
            Json.parseToJsonElement(text)
        } catch (e: SerializationException) {
            throw CatalogException("Catalogue is not valid JSON: ${e.message}")
        }
        val array = root as? JsonArray ?: throw CatalogException("Catalogue root must be an array")
        val exercises = array.mapIndexed { i, element ->
            val obj = element as? JsonObject ?: throw CatalogException("Entry $i is not an object")
            parseExercise(obj, i)
        }
        val duplicates = exercises.groupBy { it.id }.filterValues { it.size > 1 }.keys
        if (duplicates.isNotEmpty()) throw CatalogException("Duplicate exercise ids: $duplicates")
        return exercises
    }

    private fun parseExercise(obj: JsonObject, index: Int): Exercise {
        val unknown = obj.keys - knownKeys
        if (unknown.isNotEmpty()) throw CatalogException("Entry $index has unknown fields: $unknown")

        val id = obj.string("id", index)
        if (id.isBlank()) throw CatalogException("Entry $index has a blank id")
        val safety = obj.string("safety", index)
        if (safety.isBlank()) throw CatalogException("Exercise '$id' has no safety note")
        val limitations = obj.string("limitations", index)
        if (limitations.isBlank()) throw CatalogException("Exercise '$id' has no limitations note")
        val instructions = obj.stringList("instructions", index)
        if (instructions.isEmpty()) throw CatalogException("Exercise '$id' has no instructions")
        val duration = (obj["durationSeconds"] as? JsonPrimitive)?.intOrNull
            ?: throw CatalogException("Exercise '$id' has no integer durationSeconds")
        if (duration <= 0) throw CatalogException("Exercise '$id' has invalid duration")

        return Exercise(
            id = id,
            name = obj.string("name", index),
            category = enumByWire(TrainingCategory.entries, obj.string("category", index), { it.wireName }, "category", id),
            level = enumByWire(Level.entries, obj.string("level", index), { it.wireName }, "level", id),
            durationSeconds = duration,
            recommendedView = enumByWire(CameraView.entries, obj.string("recommendedView", index), { it.wireName }, "recommendedView", id),
            analysisMode = enumByWire(AnalysisMode.entries, obj.string("analysisMode", index), { it.wireName }, "analysisMode", id),
            demoAnimation = obj.string("demoAnimation", index),
            safety = safety,
            instructions = instructions,
            commonCues = obj.stringList("commonCues", index),
            limitations = limitations,
        )
    }

    private fun JsonObject.string(key: String, index: Int): String {
        val p = this[key] as? JsonPrimitive
        if (p == null || !p.isString) throw CatalogException("Entry $index: '$key' must be a string")
        return p.content
    }

    private fun JsonObject.stringList(key: String, index: Int): List<String> {
        val arr = this[key] as? JsonArray ?: throw CatalogException("Entry $index: '$key' must be an array")
        return arr.map { el ->
            val p = el as? JsonPrimitive
            if (p == null || !p.isString) throw CatalogException("Entry $index: '$key' must contain only strings")
            p.content
        }
    }

    private fun <T> enumByWire(
        values: List<T>,
        wire: String,
        nameOf: (T) -> String,
        field: String,
        id: String,
    ): T = values.firstOrNull { nameOf(it) == wire }
        ?: throw CatalogException("Exercise '$id' has unknown $field '$wire'")
}

class CatalogException(message: String) : IllegalArgumentException(message)
