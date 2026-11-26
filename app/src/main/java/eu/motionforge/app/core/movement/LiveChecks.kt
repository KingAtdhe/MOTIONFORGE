package eu.motionforge.app.core.movement

/** Which camera checks a lesson gets. Every lesson listed here was checked on rendered videos (RenderedVideoRepTest). */
object LiveChecks {
    /** The original boxing drills with their own rules (stance, jab, cross). */
    val BOXING_DRILLS = setOf("boxing_stance", "boxing_jab", "boxing_cross")

    /** True when the camera gives the lesson live feedback: counting, a hold check or the boxing guard rules. */
    fun has(id: String): Boolean =
        CountedMove.forExercise(id) != null || HoldCheck.forExercise(id) != null || id in BOXING_DRILLS || id in BoxingDrill.GUARD_CHECKED

    /** The check wants the phone low and side-on (moves on the floor). */
    fun floorLevel(id: String): Boolean =
        CountedMove.forExercise(id)?.framing?.contains("floor level") == true || HoldCheck.forExercise(id)?.framing?.contains("floor level") == true
}
