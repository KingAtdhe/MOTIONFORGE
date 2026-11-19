package eu.motionforge.app.core.model

/** The 3D coach shown in lesson demonstrations and sessions. Each has its own model and clip manifest. */
enum class Coach(val displayName: String, val manifestPath: String) {
    FEMALE("Female coach", "models/coach_f.clips.json"),
    MALE("Male coach", "models/coach_m.clips.json"),
    ;

    companion object {
        val DEFAULT = FEMALE
        fun fromName(name: String?): Coach = entries.firstOrNull { it.name == name } ?: DEFAULT
    }
}
