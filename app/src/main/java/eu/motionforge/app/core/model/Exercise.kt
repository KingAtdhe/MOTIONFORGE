package eu.motionforge.app.core.model

/** Domain model for one catalogue entry. Mirrors data/exercises.json. */
data class Exercise(
    val id: String,
    val name: String,
    val category: TrainingCategory,
    val level: Level,
    val durationSeconds: Int,
    val recommendedView: CameraView,
    val analysisMode: AnalysisMode,
    val demoAnimation: String,
    val safety: String,
    val instructions: List<String>,
    val commonCues: List<String>,
    val limitations: String,
)

enum class TrainingCategory(val wireName: String, val displayName: String) {
    FITNESS("fitness", "Fitness"),
    FIGHTING_FUNDAMENTALS("fighting_fundamentals", "Fighting Fundamentals"),
}

enum class Level(val wireName: String, val displayName: String) {
    BEGINNER("beginner", "Beginner"),
}

enum class CameraView(val wireName: String, val displayName: String) {
    FRONT("front", "Front"),
    SIDE("side", "Side"),
    FRONT_OR_SIDE("front_or_side", "Front or side"),
    FRONT_OR_DIAGONAL("front_or_diagonal", "Front or diagonal"),
    FULL_BODY("full_body", "Full body"),
}

/**
 * How much the camera is allowed to say about a movement.
 * Anything other than [LIMITED_RULE_BASED] / [GUIDED_LIMITED_FEEDBACK] / [MOVEMENT_PHASE_CUES_ONLY]
 * must never produce automated form feedback.
 */
enum class AnalysisMode(val wireName: String, val displayName: String, val allowsLiveCues: Boolean) {
    LIMITED_RULE_BASED("limited_rule_based", "Limited rule-based cues", true),
    GUIDED_LIMITED_FEEDBACK("guided_limited_feedback", "Guided setup cues", true),
    MOVEMENT_PHASE_CUES_ONLY("movement_phase_cues_only", "Movement-phase cues only", true),
    DEMO_GUIDED_INITIALLY("demo_guided_initially", "Demo and guided practice only", false),
    GUIDED_NOT_SCORED("guided_not_scored", "Guided, not scored", false),
}
