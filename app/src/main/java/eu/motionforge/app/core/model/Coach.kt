package eu.motionforge.app.core.model

/** The 3D coach shown in lesson demonstrations and sessions. Each has its own model and clip manifest. */
enum class Coach(val displayName: String, val manifestPath: String, val artDir: String) {
    FEMALE("Female coach", "models/coach_f.clips.json", "studies/coach_f"),
    MALE("Male coach", "models/coach_m.clips.json", "studies/coach_m"),
    ;

    /** A still of this coach performing a lesson: its motion study. */
    fun lessonArt(exerciseId: String) = studyArt(exerciseId)

    /** Motion study of a lesson: several exposures on one black plate (tools/compose_studies.py). */
    fun studyArt(exerciseId: String) = "${artDir}/$exerciseId.webp"

    /** Four frames of the movement side by side, for the lesson contact sheet. */
    fun stripArt(exerciseId: String) = "${artDir}/${exerciseId}_strip.webp"

    /** A representative picture of this coach: the squat study. */
    val heroArt: String get() = studyArt("bodyweight_squat")

    companion object {
        val DEFAULT = FEMALE
        fun fromName(name: String?): Coach = entries.firstOrNull { it.name == name } ?: DEFAULT
    }
}
