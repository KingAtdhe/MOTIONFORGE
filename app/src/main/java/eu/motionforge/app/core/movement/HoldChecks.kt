package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.PoseFrame
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.hypot

/** A form adjustment a hold check can name ([message] on screen, [spoken] by the voice coach). */
enum class HoldIssue(override val message: String, override val spoken: String) : FormCue {
    HIPS_SAG("Possible form adjustment: lift your hips into one line with your shoulders.", "Hips up into a line."),
    HIPS_PIKE("Possible form adjustment: lower your hips into one line with your shoulders.", "Hips down a little."),
    SIT_HIGHER_THAN_PLANNED("Possible form adjustment: slide a little lower toward a right angle, if it's comfortable.", "A little lower if it's comfortable."),
}

/**
 * Held positions the camera can check: it only says whether you are in the position (and counts the seconds you
 * hold it), plus at most one measurable adjustment. It never judges effort, safety or how long you should hold.
 */
enum class HoldCheck(val checkName: String, val framing: String, val waiting: String, val holding: String) {
    PLANK("Plank check", "Put the phone side-on at floor level, whole body in view.",
        "Get into your plank. The timer runs while you hold the position.", "Holding — steady breathing."),
    BEAR("Bear hold check", "Put the phone side-on at floor level, whole body in view.",
        "Hands under shoulders, knees under hips. The timer runs while you're on all fours.",
        "On all fours — keep the knees just off the floor."),
    WALL_SIT("Wall sit check", "Put the phone side-on, whole body in view.",
        "Slide down the wall. The timer runs while you hold the sit.", "Holding — back on the wall."),
    BALANCE("Balance check", "Face the phone with your whole body, feet included, in view.",
        "Lift one foot. The timer runs while you balance.", "Balancing — eyes on a fixed point."),
    CHILDS_POSE("Stretch check", "Put the phone side-on at floor level, whole body in view.",
        "Sit back toward your heels. The timer runs while you rest in the stretch.", "In the stretch — breathe slowly."),
    SHOULDER_STRETCH("Stretch check", "Face the phone with your upper body and both arms in view.",
        "Bring one arm across your chest. The timer runs while you hold the stretch.", "Stretching — shoulders down, breathe."),
    TRICEPS_STRETCH("Stretch check", "Face the phone with your upper body and both arms in view.",
        "Raise one elbow and drop the hand behind your head. The timer runs while you hold.", "Stretching — elbow up, head tall."),
    CHEST_OPENER("Stretch check", "Face the phone with your whole body in view.",
        "Bring your hands together behind your back. The timer runs while you hold.", "Stretching — shoulders back, chest up."),
    HIP_FLEXOR("Stretch check", "Put the phone at floor level, side-on, whole body in view.",
        "Kneel on one knee, the other foot in front. The timer runs while you hold the stretch.", "Stretching — hips forward, chest tall."),
    ARMS_OUT("Arm check", "Face the phone with your upper body and both arms in view.",
        "Lift both arms out to shoulder height. The timer runs while they're up.", "Arms up — small, smooth circles."),
    ;

    companion object {
        /** Which hold check a lesson uses, or null. Each mapping is checked on rendered videos (RenderedVideoRepTest). */
        fun forExercise(id: String): HoldCheck? = when (id) {
            "forearm_plank", "high_plank" -> PLANK
            "bear_plank_hold" -> BEAR
            "wall_sit" -> WALL_SIT
            "single_leg_balance" -> BALANCE
            "childs_pose" -> CHILDS_POSE
            "arm_circles" -> ARMS_OUT
            "cross_body_shoulder_stretch" -> SHOULDER_STRETCH
            "overhead_triceps_stretch" -> TRICEPS_STRETCH
            "chest_opener_stretch" -> CHEST_OPENER
            "kneeling_hip_flexor_stretch" -> HIP_FLEXOR
            else -> null
        }
    }
}

/**
 * What a [HoldMonitor] reports; [heldMs] is the time spent in the position during this step.
 * - [NotAssessing]: the body is not clearly seen (or tracking is off); the timer does not run.
 * - [OutOfPosition]: seen, but not in the position.
 * - [Holding]: in the position, no adjustment.
 * - [Cue]: in the position, one adjustment has held for most of the recent window.
 */
sealed interface HoldFeedback {
    val heldMs: Long

    data class NotAssessing(override val heldMs: Long) : HoldFeedback
    data class OutOfPosition(override val heldMs: Long) : HoldFeedback
    data class Holding(override val heldMs: Long) : HoldFeedback
    data class Cue(val issue: HoldIssue, override val heldMs: Long) : HoldFeedback
}

/**
 * Watches a held position. Every frame gives "in position?" and at most one issue; the state only changes when the
 * new reading holds for [persistFraction] of the last [windowMs] (one bad frame never moves the timer or gives advice).
 * Hold time only adds up while the state is in position, frame time capped at [maxStepMs] (a tracking gap is never
 * counted as holding). Thresholds were set on rendered videos of the app's coaches, for coach review.
 */
class HoldMonitor(
    val check: HoldCheck,
    private val minVisibility: Float = 0.6f,
    private val windowMs: Long = 1_000,
    private val persistFraction: Double = 0.7,
    private val maxStepMs: Long = 250,
) {
    private data class Sample(val t: Long, val seen: Boolean, val inPosition: Boolean, val issue: HoldIssue?)

    private val window = ArrayDeque<Sample>()
    private var held = 0L
    private var lastT = -1L
    private var state: HoldFeedback = HoldFeedback.NotAssessing(0)

    val heldMs: Long get() = held

    fun reset() {
        window.clear(); lastT = -1L
        state = HoldFeedback.NotAssessing(held)
    }

    /** Clears the hold time too (a new step). */
    fun restart() { held = 0L; reset() }

    fun update(frame: PoseFrame, tracking: Boolean): HoldFeedback {
        val t = frame.timestampMs
        val r = if (tracking) read(frame) else null
        window.addLast(Sample(t, r != null, r?.first == true, r?.second))
        while (window.isNotEmpty() && t - window.first().t > windowMs) window.removeFirst()
        val n = window.size
        val seen = window.count { it.seen }
        val inPos = window.count { it.inPosition }
        val next: HoldFeedback = when {
            seen < persistFraction * n -> HoldFeedback.NotAssessing(held)
            inPos >= persistFraction * n -> {
                val top = window.mapNotNull { it.issue }.groupingBy { it }.eachCount().maxByOrNull { it.value }
                if (top != null && top.value >= persistFraction * n) HoldFeedback.Cue(top.key, held) else HoldFeedback.Holding(held)
            }
            inPos <= (1 - persistFraction) * n -> HoldFeedback.OutOfPosition(held)
            else -> state // in between: keep what was shown
        }
        if (lastT >= 0 && (next is HoldFeedback.Holding || next is HoldFeedback.Cue)) held += (t - lastT).coerceIn(0, maxStepMs)
        lastT = t
        state = when (next) {
            is HoldFeedback.NotAssessing -> next.copy(heldMs = held)
            is HoldFeedback.OutOfPosition -> next.copy(heldMs = held)
            is HoldFeedback.Holding -> next.copy(heldMs = held)
            is HoldFeedback.Cue -> next.copy(heldMs = held)
        }
        return state
    }

    // ------------------------------------------------------------------ geometry (pixels, normalised by torso length)
    private fun PoseFrame.seen(vararg l: BodyLandmark) = l.all { this[it].visibility >= minVisibility }
    private fun PoseFrame.x(l: BodyLandmark) = this[l].x * imageWidth.toDouble()
    private fun PoseFrame.y(l: BodyLandmark) = this[l].y * imageHeight.toDouble()
    private fun PoseFrame.d(a: BodyLandmark, b: BodyLandmark) = hypot(x(a) - x(b), y(a) - y(b))

    private fun PoseFrame.angleAt(a: BodyLandmark, b: BodyLandmark, c: BodyLandmark): Double? {
        if (!seen(a, b, c)) return null
        val ux = x(a) - x(b); val uy = y(a) - y(b); val vx = x(c) - x(b); val vy = y(c) - y(b)
        val n = hypot(ux, uy) * hypot(vx, vy)
        if (n < 1.0) return null
        return Math.toDegrees(acos(((ux * vx + uy * vy) / n).coerceIn(-1.0, 1.0)))
    }

    /** The side nearer the camera (higher visibility of the given joints): LEFT when true. */
    private fun PoseFrame.leftNearer(vararg pairs: Pair<BodyLandmark, BodyLandmark>) =
        pairs.sumOf { this[it.first].visibility.toDouble() } >= pairs.sumOf { this[it.second].visibility.toDouble() }

    private data class Torso(val sx: Double, val sy: Double, val hx: Double, val hy: Double, val len: Double) {
        /** Angle from image vertical, degrees: 0 upright, 90 lying, 180 upside down. */
        val tilt: Double get() {
            val dy = hy - sy
            val a = Math.toDegrees(atan2(abs(sx - hx), abs(dy)))
            return if (dy < 0) 180.0 - a else a
        }
    }

    private fun PoseFrame.torso(): Torso? {
        val ls = BodyLandmark.LEFT_SHOULDER; val rs = BodyLandmark.RIGHT_SHOULDER; val lh = BodyLandmark.LEFT_HIP; val rh = BodyLandmark.RIGHT_HIP
        // side-on the far shoulder/hip are often rated low: use whichever side is seen, or both
        val left = seen(ls, lh); val right = seen(rs, rh)
        if (!left && !right) return null
        val sx = if (left && right) (x(ls) + x(rs)) / 2 else if (left) x(ls) else x(rs)
        val sy = if (left && right) (y(ls) + y(rs)) / 2 else if (left) y(ls) else y(rs)
        val hx = if (left && right) (x(lh) + x(rh)) / 2 else if (left) x(lh) else x(rh)
        val hy = if (left && right) (y(lh) + y(rh)) / 2 else if (left) y(lh) else y(rh)
        val len = hypot(sx - hx, sy - hy)
        return if (len < 5.0) null else Torso(sx, sy, hx, hy, len)
    }

    /** (in position, issue) for this frame, or null when the needed body points are not clearly seen. */
    private fun read(f: PoseFrame): Pair<Boolean, HoldIssue?>? = when (check) {
        HoldCheck.PLANK -> plank(f)
        HoldCheck.BEAR -> bear(f)
        HoldCheck.WALL_SIT -> wallSit(f)
        HoldCheck.BALANCE -> balance(f)
        HoldCheck.CHILDS_POSE -> childsPose(f)
        HoldCheck.ARMS_OUT -> armsOut(f)
        HoldCheck.SHOULDER_STRETCH -> shoulderStretch(f)
        HoldCheck.TRICEPS_STRETCH -> tricepsStretch(f)
        HoldCheck.CHEST_OPENER -> chestOpener(f)
        HoldCheck.HIP_FLEXOR -> hipFlexor(f)
    }

    /** Cross-body shoulder stretch, facing the phone: one wrist carried across past the middle of the chest, at about
     *  shoulder height. */
    private fun shoulderStretch(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val sides = listOf(BodyLandmark.LEFT_SHOULDER to BodyLandmark.LEFT_WRIST, BodyLandmark.RIGHT_SHOULDER to BodyLandmark.RIGHT_WRIST)
        if (sides.none { (sh, wr) -> f.seen(sh) && f[wr].visibility >= 0.4f }) return null
        val crossed = sides.any { (sh, wr) ->
            f.seen(sh) && f[wr].visibility >= 0.4f &&
                (f.x(wr) - tor.sx) * (f.x(sh) - tor.sx) < 0 && abs(f.x(wr) - tor.sx) / tor.len > SHOULDER_CROSS &&
                (f.y(wr) - f.y(sh)) / tor.len in -0.25..0.45      // about shoulder height, not reaching overhead
        }
        return (tor.tilt < 30.0 && crossed) to null
    }

    /** Overhead triceps stretch: one arm raised — an elbow at or above shoulder height and a hand well above the
     *  shoulders (the raised hand behind the head or the helping hand on the elbow; on the rendered videos the model
     *  puts the bent elbow just above the shoulder, not above the head). */
    private fun tricepsStretch(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val arms = listOf(
            Triple(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_ELBOW, BodyLandmark.LEFT_WRIST),
            Triple(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_ELBOW, BodyLandmark.RIGHT_WRIST),
        ).filter { (sh, el, _) -> f.seen(sh) && f[el].visibility >= 0.4f }
        if (arms.isEmpty()) return null
        val elbowUp = arms.any { (sh, el, _) -> (f.y(sh) - f.y(el)) / tor.len > TRICEPS_ELBOW_UP }
        val handUp = arms.any { (sh, _, wr) -> f[wr].visibility >= 0.3f && (f.y(sh) - f.y(wr)) / tor.len > TRICEPS_HAND_UP }
        return (tor.tilt < 30.0 && elbowUp && handUp) to null
    }

    /** Chest opener, facing the phone: standing tall with both hands together behind the back — the wrists close to
     *  the middle of the back, at lower-back height (they read through the body at lower visibility). */
    private fun chestOpener(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val w = listOf(BodyLandmark.LEFT_WRIST, BodyLandmark.RIGHT_WRIST)
        if (w.any { f[it].visibility < 0.2f }) return null
        // hands drawn in behind the back, above the hips (hanging by the sides they are ~0.6 out and just below them)
        val together = w.all { abs(f.x(it) - tor.hx) / tor.len < CHEST_HANDS_X && (tor.hy - f.y(it)) / tor.len in 0.05..0.75 }
        return (tor.tilt < 25.0 && together) to null
    }

    /** Half-kneeling hip flexor stretch, side-on: torso upright, one knee down near the floor (near the height of the
     *  lowest foot point), the other clearly higher (the front knee). */
    private fun hipFlexor(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val knees = listOf(BodyLandmark.LEFT_KNEE, BodyLandmark.RIGHT_KNEE)
        if (knees.any { f[it].visibility < 0.3f }) return null
        val feet = listOf(BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE, BodyLandmark.LEFT_FOOT_INDEX, BodyLandmark.RIGHT_FOOT_INDEX)
            .filter { f[it].visibility >= 0.3f }
        if (feet.isEmpty()) return null
        val floor = feet.maxOf { f.y(it) }
        val low = knees.maxOf { f.y(it) }; val high = knees.minOf { f.y(it) }
        val kneeDown = (floor - low) / tor.len < HIP_KNEE_DOWN
        val split = (low - high) / tor.len > HIP_KNEE_SPLIT
        return (tor.tilt < 35.0 && kneeDown && split) to null
    }

    /** Arms out: both wrists near shoulder height (within [ARMS_BAND] torso lengths) and out to the sides, beyond the
     *  shoulders by half a torso length; standing upright, facing the phone. */
    private fun armsOut(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val ok = listOf(
            Triple(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_WRIST, 1.0), Triple(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_WRIST, -1.0),
        ).map { (sh, wr, _) ->
            if (!f.seen(sh, wr)) return null
            abs(f.y(wr) - f.y(sh)) / tor.len < ARMS_BAND && abs(f.x(wr) - tor.sx) - abs(f.x(sh) - tor.sx) > 0.5 * tor.len
        }
        return (tor.tilt < 30.0 && ok.all { it }) to null
    }

    /**
     * Plank (forearms or hands): body near horizontal, the hands/elbows under the shoulders (below them in the image)
     * and the shoulder–hip–ankle line long. Side-on only for the line rule: the hips more than [PLANK_BEND] off the
     * line → sag / pike (same rule as the push-up counter).
     */
    private fun plank(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val left = f.leftNearer(BodyLandmark.LEFT_HIP to BodyLandmark.RIGHT_HIP, BodyLandmark.LEFT_ANKLE to BodyLandmark.RIGHT_ANKLE)
        val sh = if (left) BodyLandmark.LEFT_SHOULDER else BodyLandmark.RIGHT_SHOULDER
        val hp = if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP
        val an = if (left) BodyLandmark.LEFT_ANKLE else BodyLandmark.RIGHT_ANKLE
        val el = if (left) BodyLandmark.LEFT_ELBOW else BodyLandmark.RIGHT_ELBOW
        if (!f.seen(sh, hp, an)) return null
        val line = f.angleAt(sh, hp, an) ?: return null
        val support = f.seen(el) && f.y(el) > f.y(sh)
        val inPos = tor.tilt in 60.0..120.0 && support && line > 150.0
        if (!inPos) return false to null
        var issue: HoldIssue? = null
        if (180.0 - line > PLANK_BEND) {
            val sx = f.x(sh); val sy = f.y(sh); val ex = f.x(an); val ey = f.y(an)
            val tt = ((f.x(hp) - sx) / (ex - sx).let { if (abs(it) < 1e-6) 1e-6 else it }).coerceIn(0.0, 1.0)
            issue = if (f.y(hp) > sy + (ey - sy) * tt) HoldIssue.HIPS_SAG else HoldIssue.HIPS_PIKE
        }
        return true to issue
    }

    /** Bear hold: on all fours — torso near horizontal, knees bent (hip–knee–ankle), hands under the shoulders. The
     *  knees hover only 2–3 cm: on the rendered videos that is 0.03–0.1 torso lengths depending on the body and the
     *  camera, too close to landmark noise to tell hovering from resting, so only the position is checked. */
    private fun bear(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val left = f.leftNearer(BodyLandmark.LEFT_KNEE to BodyLandmark.RIGHT_KNEE, BodyLandmark.LEFT_ANKLE to BodyLandmark.RIGHT_ANKLE)
        val hp = if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP
        val kn = if (left) BodyLandmark.LEFT_KNEE else BodyLandmark.RIGHT_KNEE
        val an = if (left) BodyLandmark.LEFT_ANKLE else BodyLandmark.RIGHT_ANKLE
        val sh = if (left) BodyLandmark.LEFT_SHOULDER else BodyLandmark.RIGHT_SHOULDER
        val wr = if (left) BodyLandmark.LEFT_WRIST else BodyLandmark.RIGHT_WRIST
        val knee = f.angleAt(hp, kn, an) ?: return null
        if (!f.seen(sh, wr)) return null
        val inPos = tor.tilt in 55.0..125.0 && knee in 60.0..135.0 && f.y(wr) > f.y(sh)
        return inPos to null
    }

    /** Wall sit: torso upright, knees bent (hip–knee–ankle up to [WALL_SIT_MAX_KNEE]); above [WALL_SIT_HIGH] (but
     *  still clearly sitting) the cue suggests sliding a little lower. */
    private fun wallSit(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val left = f.leftNearer(BodyLandmark.LEFT_KNEE to BodyLandmark.RIGHT_KNEE, BodyLandmark.LEFT_ANKLE to BodyLandmark.RIGHT_ANKLE)
        val knee = f.angleAt(
            if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP,
            if (left) BodyLandmark.LEFT_KNEE else BodyLandmark.RIGHT_KNEE,
            if (left) BodyLandmark.LEFT_ANKLE else BodyLandmark.RIGHT_ANKLE,
        ) ?: return null
        val inPos = tor.tilt < 35.0 && knee in 60.0..WALL_SIT_MAX_KNEE
        return inPos to (if (inPos && knee > WALL_SIT_HIGH) HoldIssue.SIT_HIGHER_THAN_PLANNED else null)
    }

    /** Single-leg balance: torso upright and one foot clearly lifted — its ankle and knee both above the other leg's. */
    private fun balance(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        if (f[BodyLandmark.LEFT_ANKLE].visibility < 0.5f || f[BodyLandmark.RIGHT_ANKLE].visibility < 0.5f) return null
        if (f[BodyLandmark.LEFT_KNEE].visibility < 0.5f || f[BodyLandmark.RIGHT_KNEE].visibility < 0.5f) return null
        // the lifted foot's knee comes up too (a staggered stance seen from the front puts the far ankle higher in the
        // picture, ~0.2 torso lengths, but its knee only ~0.05)
        val lift = abs(f.y(BodyLandmark.LEFT_ANKLE) - f.y(BodyLandmark.RIGHT_ANKLE)) / tor.len
        val knee = abs(f.y(BodyLandmark.LEFT_KNEE) - f.y(BodyLandmark.RIGHT_KNEE)) / tor.len
        return (tor.tilt < 35.0 && lift > BALANCE_LIFT && knee > BALANCE_LIFT) to null
    }

    /** Child's pose: hips back over the heels and the chest folded down — the hips low (near the knees/heels) and the
     *  torso pitched forward toward horizontal or past it. */
    private fun childsPose(f: PoseFrame): Pair<Boolean, HoldIssue?>? {
        val tor = f.torso() ?: return null
        val left = f.leftNearer(BodyLandmark.LEFT_KNEE to BodyLandmark.RIGHT_KNEE, BodyLandmark.LEFT_HIP to BodyLandmark.RIGHT_HIP)
        val hp = if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP
        val kn = if (left) BodyLandmark.LEFT_KNEE else BodyLandmark.RIGHT_KNEE
        val an = if (left) BodyLandmark.LEFT_ANKLE else BodyLandmark.RIGHT_ANKLE
        val knee = f.angleAt(hp, kn, an) ?: return null
        return (knee < CHILD_KNEE && tor.tilt > 55.0) to null
    }

    companion object {
        const val PLANK_BEND = 15.0
        const val WALL_SIT_MAX_KNEE = 150.0
        const val WALL_SIT_HIGH = 125.0
        const val BALANCE_LIFT = 0.15
        const val CHILD_KNEE = 70.0
        const val ARMS_BAND = 0.45
        const val SHOULDER_CROSS = 0.08
        const val TRICEPS_ELBOW_UP = -0.05
        const val TRICEPS_HAND_UP = 0.20
        const val CHEST_HANDS_X = 0.36
        const val HIP_KNEE_DOWN = 0.40
        const val HIP_KNEE_SPLIT = 0.30
    }
}
