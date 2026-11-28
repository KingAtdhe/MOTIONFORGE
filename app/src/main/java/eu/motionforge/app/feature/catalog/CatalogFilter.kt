package eu.motionforge.app.feature.catalog

import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal

/** Duration buckets offered in the catalogue filter. */
enum class DurationFilter(val label: String, val maxSeconds: Int?) {
    ANY("Any length", null),
    UP_TO_45("≤ 45 s", 45),
    UP_TO_60("≤ 60 s", 60),
}

/** Equipment buckets offered in the catalogue filter. */
enum class EquipmentFilter(val label: String) {
    ANY("Any equipment"),
    NONE("No equipment"),
    WITH("With equipment"),
}

/** Level buckets offered in the catalogue filter. */
enum class LevelFilter(val label: String, val level: eu.motionforge.app.core.model.Level?) {
    ANY("Any level", null),
    BEGINNER("Beginner", eu.motionforge.app.core.model.Level.BEGINNER),
    INTERMEDIATE("Intermediate", eu.motionforge.app.core.model.Level.INTERMEDIATE),
}

/** Catalogue filter: category, length, equipment, level and a text search. */
data class CatalogFilter(
    val category: TrainingCategory? = null,
    val duration: DurationFilter = DurationFilter.ANY,
    val equipment: EquipmentFilter = EquipmentFilter.ANY,
    /** Text typed in the search bar; blank = no search. */
    val query: String = "",
    val level: LevelFilter = LevelFilter.ANY,
) {
    val isActive: Boolean get() = category != null || duration != DurationFilter.ANY || equipment != EquipmentFilter.ANY || query.isNotBlank() ||
        level != LevelFilter.ANY

    fun apply(exercises: List<Exercise>): List<Exercise> = CatalogSearch.search(exercises, query).filter { e ->
        (category == null || e.category == category) &&
            (duration.maxSeconds == null || e.durationSeconds <= duration.maxSeconds) &&
            (level.level == null || e.level == level.level) &&
            when (equipment) {
                EquipmentFilter.ANY -> true
                EquipmentFilter.NONE -> !e.needsEquipment
                EquipmentFilter.WITH -> e.needsEquipment
            }
    }
}

object LessonSuggestions {

    /**
     * Picks one suggested lesson for Home. Pure and deterministic:
     * - Stay in the user's chosen focus.
     * - "Build a routine" starts with the warm-up when one exists.
     * - Otherwise start with the first lesson of the focus, in catalogue order (beginner-first).
     * - Never suggest the lesson the user just viewed if another exists.
     */
    fun suggest(
        catalog: List<Exercise>,
        focus: TrainingCategory?,
        goal: TrainingGoal?,
        lastViewedId: String?,
    ): Exercise? {
        val pool = catalog.filter { focus == null || it.category == focus }.ifEmpty { catalog }
        val ordered = if (goal == TrainingGoal.BUILD_ROUTINE) {
            pool.sortedBy { if (it.id == WARM_UP_ID) 0 else 1 }
        } else {
            pool
        }
        return ordered.firstOrNull { it.id != lastViewedId } ?: ordered.firstOrNull()
    }

    const val WARM_UP_ID = "standing_mobility_warmup"
}
