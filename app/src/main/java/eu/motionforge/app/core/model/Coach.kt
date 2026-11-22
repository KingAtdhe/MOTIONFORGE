package eu.motionforge.app.core.model

/** The 3D coach shown in lesson demonstrations and sessions. Each has its own model and clip manifest. */
enum class Coach(val displayName: String, val manifestPath: String, val artDir: String) {
    FEMALE("Female coach", "models/coach_f.clips.json", "thumbs/coach_f"),
    MALE("Male coach", "models/coach_m.clips.json", "thumbs/coach_m"),
    ;

    /** Rendered still of this coach performing a lesson (tools/blender/render_thumbs.py). */
    fun lessonArt(exerciseId: String) = "$artDir/$exerciseId.webp"

    /** Motion study of a lesson: several exposures on one black plate (tools/compose_studies.py). */
    fun studyArt(exerciseId: String) = "${artDir.replace("thumbs/", "studies/")}/$exerciseId.webp"

    /** Four frames of the movement side by side, for the lesson contact sheet. */
    fun stripArt(exerciseId: String) = "${artDir.replace("thumbs/", "studies/")}/${exerciseId}_strip.webp"

    /** Full-height portrait in guard, for the home screen. */
    val heroArt: String get() = "$artDir/hero.webp"

    companion object {
        val DEFAULT = FEMALE
        fun fromName(name: String?): Coach = entries.firstOrNull { it.name == name } ?: DEFAULT
    }
}
