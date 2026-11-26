package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFrame
import eu.motionforge.app.core.pose.PoseGeometry
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot

/** Tracking gaps up to this long keep a rep in progress (one missed frame plus the tracking gate re-settling). */
const val MAX_BLIP_MS = 500L

/** A form adjustment a rep counter can name. [message] is shown on screen, [spoken] is said by the voice coach. */
interface FormCue {
    val message: String
    val spoken: String
}

/** Where a counted movement is in its cycle: TOP is the start/end position (standing, arms straight). */
enum class RepPhase { UNKNOWN, TOP, DESCENDING, BOTTOM }

/** Something worth telling the person about, produced once at the end of a movement cycle. */
sealed interface RepEvent {
    /** A counted repetition; [issues] in priority order, empty when no rule found anything to adjust. */
    data class RepCompleted(val rep: Int, val issues: Set<FormCue>) : RepEvent

    /** A clear dip that did not reach counting depth and was not counted. */
    data object ShallowRep : RepEvent
}

/** [angle] is the movement's measured signal: knee angle (squat), elbow angle (push-up), hip height vs standing (lunge). */
data class RepUpdate(val count: Int, val phase: RepPhase, val angle: Double?, val event: RepEvent? = null)

interface RepCounter {
    val repetitions: Int
    fun reset()
    fun update(frame: PoseFrame, tracking: Boolean): RepUpdate
}

/** The movements the camera can count, with the words the coaching card uses for them. */
enum class CountedMove(val checkName: String, val framing: String, val idle: String, val shallow: String) {
    SQUAT("Squat check", "Keep your whole body in view, side-on or facing the phone.",
        "Lower with control. Each rep is checked when you stand up.",
        "That dip didn't reach counting depth. Go a little lower if it's comfortable."),
    PUSH_UP("Push-up check", "Put the phone at floor level, side-on or at an angle, whole body in view.",
        "Lower with control. Each rep is checked when your arms are straight again.",
        "That one didn't reach counting depth. Lower your chest a little more if it's comfortable."),
    LUNGE("Lunge check", "Keep your whole body in view, side-on or facing the phone.",
        "Step back and lower with control. Each lunge is counted when you stand tall.",
        "That lunge didn't reach counting depth. Bend the knees a little more if it's comfortable."),
    ARM_LIFT("Rep check", "Keep your upper body and arms in view, facing the phone or side-on.",
        "Each rep is counted when the weights come back down.",
        "That one didn't go the full way. Use the full range if it's comfortable."),
    ROW("Row check", "Keep your whole body in view, side-on or at an angle.",
        "Pull with control. Each rep is counted when the arms are long again.",
        "That one didn't go the full way."),
    BAND("Band check", "Face the phone with your upper body and arms in view.",
        "Each rep is counted when your hands come back together.",
        "That one didn't go the full way."),
    HINGE("Hinge check", "Keep your whole body in view, side-on, at an angle or facing the phone.",
        "Hinge with control. Each rep is counted when you stand tall.",
        "That one didn't go the full way."),
    BRIDGE("Bridge check", "Put the phone side-on at floor level, body in view.",
        "Each rep is counted when your hips come back down.",
        "That one didn't go the full way."),
    PUNCH("Punch check", "Face the phone with your upper body and both arms in view — turned away, the far arm is hidden.",
        "Each punch is counted when your hand comes back to guard.",
        "That one didn't come up fully."),
    COMBO("Combination check", "Face the phone with your upper body and both arms in view — turned away, the far arm is hidden.",
        "Each combination is counted when your hands are back in guard.",
        "That one didn't come up fully."),
    LEVEL("Level check", "Face the phone with your whole body in view, feet included.",
        "Each body shot is counted when you come back up to your stance.",
        "That one was shallow. Bend the knees a little more if it's comfortable."),
    SLIP("Slip check", "Face the phone with your head and upper body in view.",
        "Each slip is counted when your head comes back to the middle.",
        "That one was small. Move your head a little further off the line if it's comfortable."),
    CALF_RAISE("Calf raise check", "Stand side-on to the phone with your whole body, feet included, in view.",
        "Each rep is counted when your heels come back down.",
        "That one didn't go the full way."),
    KNEE_LIFT("Knee check", "Keep your whole body in view, facing the phone or side-on.",
        "Each knee lift is counted when the foot comes back down.",
        "That one was low. Lift the knee a little higher if it's comfortable."),
    SIDE_KNEE_LIFT("Knee check", "Face the phone with your whole body in view.",
        "Each knee lift is counted when the foot comes back down.",
        "That one was low. Lift the knee a little higher if it's comfortable."),
    OVERHEAD("Triceps check", "Keep your upper body and arms in view, hands visible above your head.",
        "Each rep is counted when your arms are straight overhead again.",
        "That one didn't go the full way."),
    // ---- added 2026-11-25: each checked on rendered videos of both coaches (RenderedVideoRepTest) ----
    CLIMBER("Climber check", "Put the phone at floor level, side-on, whole body in view.",
        "Drive one knee in at a time. Each knee drive is counted when the foot goes back.",
        "That knee didn't come in far. Bring it a little closer to your chest if it's comfortable."),
    DEAD_BUG("Dead bug check", "Put the phone at floor level, side-on, whole body in view.",
        "Reach long and slow. Each leg reach is counted when it comes back.",
        "That reach was short. Lengthen the leg a little more if it's comfortable."),
    BIRD_DOG("Bird dog check", "Put the phone at floor level, side-on, whole body in view.",
        "Reach long and slow. Each reach is counted when the knee comes back down.",
        "That reach was short. Lengthen the leg a little more if it's comfortable."),
    SUPERMAN("Superman check", "Put the phone at floor level, side-on, whole body in view.",
        "Lift gently and lower. Each lift is counted when you're back down.",
        "That lift was small. Lift a little more if it's comfortable."),
    CAT_COW("Cat-cow check", "Put the phone at floor level, side-on, whole body in view.",
        "Move slowly with your breath. Each round is counted when the head comes back down.",
        "That round was small. Move a little further if it's comfortable."),
    LEG_SWING("Leg check", "Keep your whole body in view: side-on for kickbacks, facing the phone for side raises.",
        "Lift with control. Each lift is counted when the foot comes back down.",
        "That lift was small. Lift a little more if it's comfortable."),
    BUTT_KICK("Butt kick check", "Stand side-on to the phone with your whole body in view.",
        "Bring the heel up behind you. Each kick is counted when the foot comes back down.",
        "That kick was low. Bring the heel a little higher if it's comfortable."),
    TWIST("Twist check", "Face the phone with your whole body in view, hands together at your chest.",
        "Turn from the middle. Each twist is counted when you're back facing the phone.",
        "That twist was small. Turn a little further if it's comfortable."),
    SIDE_BEND("Side bend check", "Face the phone with your upper body in view.",
        "Bend to the side and come back up. Each bend is counted when you're upright again.",
        "That bend was small. Reach a little further if it's comfortable."),
    SKATE("Skater check", "Face the phone with your whole body in view, with room to step side to side.",
        "Step wide side to side. Each skate is counted when you land.",
        "That step was short. Go a little wider if it's comfortable."),
    WALL_PUSH_UP("Wall push-up check", "Stand side-on to the phone, whole body and the wall in view.",
        "Lower your chest toward the wall. Each rep is counted when your arms are straight again.",
        "That one didn't reach counting depth. Bring your chest a little closer to the wall if it's comfortable."),
    FLOOR_PRESS("Press check", "Put the phone at floor level, side-on, whole body in view.",
        "Press up and lower with control. Each press is counted when the weights come back down.",
        "That press didn't go the full way."),
    DIP("Dip check", "Put the phone side-on, whole body and the bench in view.",
        "Lower with control. Each dip is counted when your arms are straight again.",
        "That dip was shallow. Lower a little more if it's comfortable."),
    CRUNCH("Crunch check", "Put the phone at floor level, side-on, whole body in view.",
        "Curl up and lower slowly. Each crunch is counted when your shoulders come back down.",
        "That crunch was small. Curl a little more if it's comfortable."),
    KNEES_IN("Knee check", "Put the phone at floor level, side-on, whole body in view.",
        "Bring the knees in and lower slowly. Each rep is counted when the legs go back out.",
        "That one was small. Bring the knees in a little more if it's comfortable."),
    TOE_TAP("Toe tap check", "Put the phone at floor level, side-on, whole body in view.",
        "Lower one foot to tap and bring it back. Each tap is counted when the leg is back up.",
        "That tap didn't go far down."),
    HEEL_TAP("Heel tap check", "Put the phone at floor level, side-on, whole body in view.",
        "Reach side to side toward your heels. Each tap is counted when you're back in the middle.",
        "That reach was small. Reach a little further if it's comfortable."),
    SHOULDER_TAP("Shoulder tap check", "Phone at floor level at a front corner, whole body in view (side-on or head-on, a hand or the legs get hidden).",
        "Lift one hand to the other shoulder. Each tap is counted when the hand is back down.",
        "That tap was small."),
    PULL_BACK("Pull-back check", "Stand at an angle to the phone (a front corner), whole body in view.",
        "Lean back from the hips and return. Each pull-back is counted when your head is back over your stance.",
        "That one was small. Lean back a little further if it's comfortable."),
    BLOCK_COUNTER("Block-and-counter check", "Stand at an angle to the phone (a front corner), whole body in view.",
        "Block, then fire the cross. Each block-and-counter is counted when both hands are back in guard.",
        "That one was small."),
    SWING("Swing check", "Stand side-on to the phone with your whole body in view.",
        "Hinge and snap the hips through. Each swing is counted when you stand tall.",
        "That one was small. Hinge a little deeper if it's comfortable."),
    SHRUG("Shrug check", "Face the phone with your head and shoulders in view.",
        "Lift the shoulders toward your ears and lower slowly. Each shrug is counted when they're back down.",
        "That shrug was small. Lift a little higher if it's comfortable."),
    KICK_BACK("Leg lift check", "Phone at floor level at a front corner on the working leg's side, whole body in view.",
        "Lift the leg with control. Each lift is counted when the knee comes back down.",
        "That lift was small. Lift a little more if it's comfortable."),
    ;

    companion object {
        /** Which counter a lesson uses, or null when the camera does not count that lesson. */
        fun forExercise(id: String): CountedMove? = when (id) {
            "bodyweight_squat", "sumo_squat", "dumbbell_squat", "dumbbell_goblet_squat" -> SQUAT
            "push_up", "knee_push_up", "incline_push_up" -> PUSH_UP
            "reverse_lunge", "split_squat", "forward_lunge", "side_lunge", "dumbbell_reverse_lunge",
            "curtsy_lunge" -> LUNGE
            "dumbbell_biceps_curl", "dumbbell_shoulder_press", "dumbbell_lateral_raise", "step_jack",
            "dumbbell_hammer_curl", "dumbbell_front_raise" -> ARM_LIFT
            "dumbbell_overhead_triceps_extension" -> OVERHEAD
            "dumbbell_bent_over_row", "dumbbell_reverse_fly" -> ROW
            "band_pull_apart" -> BAND
            // the bodyweight hip hinge stays instructional only (spec); the loaded hinges are counted, never judged
            "dumbbell_romanian_deadlift", "kettlebell_deadlift", "good_morning", "single_leg_rdl" -> HINGE
            "glute_bridge" -> BRIDGE
            "boxing_lead_hook", "boxing_rear_hook", "boxing_lead_uppercut", "boxing_rear_uppercut",
            "boxing_one_two", "boxing_one_two_hook", "boxing_step_jab",
            "boxing_back_jab", "boxing_lateral_jab", "boxing_jab_pivot" -> PUNCH
            "boxing_body_jab", "boxing_body_cross", "boxing_body_hook", "boxing_rear_body_hook" -> LEVEL
            "boxing_jab_jab_cross", "boxing_double_jab", "boxing_cross_hook",
            "boxing_jab_body_cross", "boxing_jab_uppercut", "boxing_uppercut_hook", "boxing_hook_cross",
            "boxing_cross_hook_cross", "boxing_one_two_uppercut", "boxing_uppercuts" -> COMBO
            "high_knee_march", "standing_knee_crunch" -> KNEE_LIFT
            "standing_oblique_crunch" -> SIDE_KNEE_LIFT
            "boxing_slip", "boxing_jab_slip" -> SLIP
            "calf_raise", "dumbbell_calf_raise" -> CALF_RAISE
            "squat_calf_raise" -> SQUAT
            "boxing_roll", "boxing_duck" -> LEVEL
            "slow_mountain_climber" -> CLIMBER
            "dead_bug" -> DEAD_BUG
            "bird_dog" -> BIRD_DOG
            "superman" -> SUPERMAN
            "cat_cow" -> CAT_COW
            "glute_kickback", "side_leg_raise" -> LEG_SWING
            "butt_kicks" -> BUTT_KICK
            "standing_torso_twist" -> TWIST
            "standing_side_bend" -> SIDE_BEND
            "skater_step" -> SKATE
            "wall_push_up" -> WALL_PUSH_UP
            "dumbbell_floor_press" -> FLOOR_PRESS
            "bench_dip" -> DIP
            "crunch" -> CRUNCH
            "reverse_crunch" -> KNEES_IN
            "tabletop_toe_taps" -> TOE_TAP
            "plank_shoulder_taps" -> SHOULDER_TAP
            "heel_taps" -> HEEL_TAP
            "donkey_kick", "fire_hydrant" -> KICK_BACK
            "dumbbell_shrug" -> SHRUG
            "kettlebell_swing" -> SWING
            "boxing_pull_back", "boxing_pull_counter" -> PULL_BACK
            "boxing_block_cross" -> BLOCK_COUNTER
            "single_leg_glute_bridge" -> BRIDGE
            "boxing_roll_hook", "boxing_body_head_jab" -> COMBO
            else -> null
        }

        /** How far the wrists must rise (torso lengths) for each arm-lift lesson. */
        private val ARM_TRAVEL = mapOf(
            "dumbbell_biceps_curl" to 0.45, "dumbbell_shoulder_press" to 0.45, "dumbbell_lateral_raise" to 0.40, "step_jack" to 0.90,
            "dumbbell_hammer_curl" to 0.45, "dumbbell_front_raise" to 0.40,
        )

        fun counterFor(id: String): RepCounter? = when (forExercise(id)) {
            SQUAT -> SquatRepCounter()
            PUSH_UP -> PushUpRepCounter(bodyLineToKnees = id == "knee_push_up")
            LUNGE -> if (id == "side_lunge") SideLungeRepCounter() else LungeRepCounter()
            ARM_LIFT -> ArmLiftRepCounter(travel = ARM_TRAVEL.getValue(id), minRepMs = if (id == "step_jack") 300 else 700)
            ROW -> RowRepCounter()
            BAND -> BandPullRepCounter()
            HINGE -> HingeRepCounter()
            BRIDGE -> BridgeRepCounter()
            CALF_RAISE -> CalfRaiseRepCounter()
            PUNCH -> PunchRepCounter()
            COMBO -> ComboRepCounter()
            LEVEL -> LevelChangeRepCounter()
            SLIP -> SlipRepCounter()
            KNEE_LIFT -> KneeLiftRepCounter()
            // the knee goes out to the side, so it rises less (peaks ~0.47 above standing, against ~0.6 in front)
            SIDE_KNEE_LIFT -> KneeLiftRepCounter(travel = 0.38)
            OVERHEAD -> OverheadDropRepCounter()
            null -> null
            else -> MoreMoves.counterFor(forExercise(id)!!)
        }
    }
}

/**
 * Shared repetition engine: one rep is a full cycle  top → bottom → top  of a smoothed joint angle.
 * Same safety rules as the squat counter: a frame without the needed landmarks (or with tracking off) resets the
 * cycle, so a rep can never be completed across a tracking gap; a cycle faster than [minRepMs] is ignored; a form
 * rule needs [minRuleFrames] qualifying bottom frames and most of them before it becomes a cue.
 */
abstract class CycleRepCounter(
    private val topAngle: Double,
    private val bottomAngle: Double,
    private val shallowAngle: Double,
    private val minRepMs: Long = 700,
    private val smoothingWindow: Int = 3,
    protected val minVisibility: Float = 0.6f,
    protected val minRuleFrames: Int = 3,
    protected val ruleFraction: Double = 0.6,
    /** How far below [topAngle] the signal must go before a descent starts (same units as the signal). */
    private val descentMargin: Double = 10.0,
    /** Frames within this much of [bottomAngle] are "at the bottom" for the form rules. */
    private val bottomBand: Double = 8.0,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN

    /** Where the current cycle is (subclasses that normalise their signal need it). */
    protected val currentPhase: RepPhase get() = phase
    private var cycleStartMs = 0L
    private var minAngle = 180.0
    private val window = ArrayDeque<Double>()

    override val repetitions: Int get() = count

    /** The movement's angle in this frame, or null when it cannot be measured (or the body is not in position). */
    protected abstract fun angle(f: PoseFrame): Double?

    /** Called for frames near the bottom of the cycle, to collect form measurements. */
    protected open fun observeBottom(f: PoseFrame) {}

    /** The cues for the cycle that just ended; called once per counted rep. */
    protected open fun cuesOfCycle(): Set<FormCue> = emptySet()

    /** Clears the per-cycle form measurements. */
    protected open fun startCycle() {}

    override fun reset() {
        count = 0
        lose()
    }

    private var lastGoodMs = -1L

    private fun lose() {
        lastGoodMs = -1L
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) angle(frame) else null
        if (raw == null) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, phase, null)
            lose()
            return RepUpdate(count, phase, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val a = window.average()
        val t = frame.timestampMs
        var event: RepEvent? = null
        if (phase == RepPhase.DESCENDING || phase == RepPhase.BOTTOM) minAngle = minOf(minAngle, a)
        when (phase) {
            RepPhase.UNKNOWN -> if (a >= topAngle) phase = RepPhase.TOP
            RepPhase.TOP -> if (a < topAngle - descentMargin) {
                phase = RepPhase.DESCENDING
                cycleStartMs = t
                minAngle = a
                startCycle()
            }
            RepPhase.DESCENDING -> when {
                a <= bottomAngle -> phase = RepPhase.BOTTOM
                a >= topAngle -> {
                    if (minAngle <= shallowAngle) event = RepEvent.ShallowRep
                    phase = RepPhase.TOP
                }
            }
            RepPhase.BOTTOM -> if (a >= topAngle) {
                if (t - cycleStartMs >= minRepMs) {
                    count++
                    event = RepEvent.RepCompleted(count, cuesOfCycle())
                }
                phase = RepPhase.TOP
            }
        }
        if (phase == RepPhase.BOTTOM && a <= bottomAngle + bottomBand) observeBottom(frame)
        return RepUpdate(count, phase, a, event)
    }

    protected fun PoseFrame.visible(vararg l: BodyLandmark) = l.all { this[it].visibility >= minVisibility }

    protected fun PoseFrame.px(a: Landmark, b: Landmark) = hypot((a.x - b.x) * imageWidth.toDouble(), (a.y - b.y) * imageHeight.toDouble())

    protected fun PoseFrame.angleAt(a: BodyLandmark, b: BodyLandmark, c: BodyLandmark): Double? =
        if (visible(a, b, c)) PoseGeometry.angleDegrees2d(this[a], this[b], this[c], imageWidth, imageHeight) else null

    /** Mid-point of two landmarks in pixels. */
    protected fun PoseFrame.mid(a: BodyLandmark, b: BodyLandmark) =
        ((this[a].x + this[b].x) / 2.0 * imageWidth) to ((this[a].y + this[b].y) / 2.0 * imageHeight)

    /** Angle of the hip→shoulder line from image vertical, degrees (0 = upright, 90 = lying flat). */
    protected fun PoseFrame.torsoFromVertical(): Double? {
        if (!visible(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER) &&
            !(visible(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_HIP) || visible(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_HIP))
        ) return null
        val s = mid(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER)
        val h = mid(BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)
        return Math.toDegrees(atan2(abs(s.first - h.first), h.second - s.second)).let { if (h.second - s.second < 0) 180.0 - it else it }
    }

    /** Shoulder width over torso length: large when the person faces the camera, small when side-on. */
    protected fun PoseFrame.frontalRatio(): Double? {
        if (!visible(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val torso = (px(this[BodyLandmark.LEFT_SHOULDER], this[BodyLandmark.LEFT_HIP]) + px(this[BodyLandmark.RIGHT_SHOULDER], this[BodyLandmark.RIGHT_HIP])) / 2
        if (torso < 5.0) return null
        return px(this[BodyLandmark.LEFT_SHOULDER], this[BodyLandmark.RIGHT_SHOULDER]) / torso
    }

}

enum class PushUpIssue(override val message: String, override val spoken: String) : FormCue {
    HIPS_SAG("Possible form adjustment: lift your hips into one line with your shoulders.", "Hips up into a line."),
    HIPS_PIKE("Possible form adjustment: lower your hips into one line with your shoulders.", "Hips down a little."),
}

/**
 * Push-up counter: the elbow angle (shoulder–elbow–wrist, averaged over the clearly visible arms) cycles from
 * straight ([topAngle]) to bent ([bottomAngle]). Only measured while the body is in a push-up position: the torso
 * clearly away from upright ([minTorsoTilt] from vertical, side-ish views) or strongly foreshortened (head-on
 * views), and the wrists below the shoulders — so arm movements while standing are never counted.
 *
 * Form rule, side-on only, at the bottom: the shoulder–hip–ankle line (shoulder–hip–knee for knee push-ups) bends
 * more than [maxLineBend]; the hips below that line → [PushUpIssue.HIPS_SAG], above → [PushUpIssue.HIPS_PIKE].
 * Thresholds are first hypotheses for coach review, checked against rendered test videos (see docs/BUILD_LOG.md).
 */
class PushUpRepCounter(
    private val bodyLineToKnees: Boolean = false,
    // a phone on the floor sees the straight arm at the top foreshortened (~140–150° on the rendered test videos)
    topAngle: Double = 135.0,
    bottomAngle: Double = 105.0,
    shallowAngle: Double = 120.0,
    private val minTorsoTilt: Double = 45.0,
    private val maxForeshortened: Double = 0.75,
    private val maxLineBend: Double = 15.0,
) : CycleRepCounter(topAngle, bottomAngle, shallowAngle) {
    private var sideBottom = 0
    private var sag = 0
    private var pike = 0

    override fun startCycle() { sideBottom = 0; sag = 0; pike = 0 }

    override fun angle(f: PoseFrame): Double? {
        val arms = listOfNotNull(
            f.angleAt(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_ELBOW, BodyLandmark.LEFT_WRIST),
            f.angleAt(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_ELBOW, BodyLandmark.RIGHT_WRIST),
        )
        if (arms.isEmpty() || !inPosition(f)) return null
        return arms.average()
    }

    private fun inPosition(f: PoseFrame): Boolean {
        val tilt = f.torsoFromVertical() ?: return false
        val wristsBelow = listOf(
            BodyLandmark.LEFT_SHOULDER to BodyLandmark.LEFT_WRIST, BodyLandmark.RIGHT_SHOULDER to BodyLandmark.RIGHT_WRIST,
        ).filter { (s, w) -> f.visible(s, w) }.let { pairs -> pairs.isNotEmpty() && pairs.all { (s, w) -> f[w].y > f[s].y } }
        if (!wristsBelow) return false
        if (tilt >= minTorsoTilt) return true
        val fr = f.frontalRatio() ?: return false
        return fr >= 1.0 / maxForeshortened // head-on: the torso is foreshortened to well under the shoulder width
    }

    override fun observeBottom(f: PoseFrame) {
        val fr = f.frontalRatio() ?: return
        if (fr > 0.45) return // only side-ish views show the body line
        val far = if (bodyLineToKnees) BodyLandmark.LEFT_KNEE to BodyLandmark.RIGHT_KNEE else BodyLandmark.LEFT_ANKLE to BodyLandmark.RIGHT_ANKLE
        // the side nearer the camera (higher visibility) gives the cleaner line
        val left = f[BodyLandmark.LEFT_HIP].visibility + f[far.first].visibility >= f[BodyLandmark.RIGHT_HIP].visibility + f[far.second].visibility
        val sh = if (left) BodyLandmark.LEFT_SHOULDER else BodyLandmark.RIGHT_SHOULDER
        val hp = if (left) BodyLandmark.LEFT_HIP else BodyLandmark.RIGHT_HIP
        val end = if (left) far.first else far.second
        val ang = f.angleAt(sh, hp, end) ?: return
        sideBottom++
        if (180.0 - ang > maxLineBend) {
            // which side of the shoulder→end line the hip is on (image y grows downward)
            val s = f[sh]; val h = f[hp]; val e = f[end]
            val tt = ((h.x - s.x) / (e.x - s.x).let { if (abs(it) < 1e-6) 1e-6f else it }).coerceIn(0f, 1f)
            val lineY = s.y + (e.y - s.y) * tt
            if (h.y > lineY) sag++ else pike++
        }
    }

    override fun cuesOfCycle(): Set<FormCue> = buildSet {
        if (sideBottom >= minRuleFrames) {
            if (sag >= ruleFraction * sideBottom) add(PushUpIssue.HIPS_SAG)
            else if (pike >= ruleFraction * sideBottom) add(PushUpIssue.HIPS_PIKE)
        }
    }
}

/**
 * Side lunge, filmed from the front: the working knee bends sideways in plain view (rendered test videos: 174° standing,
 * ~125° at the bottom), while the wide stance lowers the hips too little for the lunge's hip-height rule. Counts the
 * more-bent knee from [topAngle] down past [bottomAngle] and back, while the torso stays fairly upright.
 */
class SideLungeRepCounter(
    // at an angle the far knee reads ~156–168° even standing, and only ~0.6 s of a lunge shows below 140°
    topAngle: Double = 152.0,
    bottomAngle: Double = 140.0,
    shallowAngle: Double = 146.0,
    private val maxTilt: Double = 50.0,
) : CycleRepCounter(topAngle, bottomAngle, shallowAngle, minRepMs = 500) {
    override fun angle(f: PoseFrame): Double? {
        val tilt = f.torsoFromVertical() ?: return null
        if (tilt > maxTilt) return null
        val knees = listOfNotNull(
            f.angleAt(BodyLandmark.LEFT_HIP, BodyLandmark.LEFT_KNEE, BodyLandmark.LEFT_ANKLE),
            f.angleAt(BodyLandmark.RIGHT_HIP, BodyLandmark.RIGHT_KNEE, BodyLandmark.RIGHT_ANKLE),
        )
        return knees.minOrNull()
    }
}

enum class LungeIssue(override val message: String, override val spoken: String) : FormCue {
    LEANING("Possible form adjustment: keep your chest tall as you lower.", "Chest tall."),
}

/**
 * Lunge counter (reverse lunge, split squat). The signal is how high the hips are: the vertical distance from the
 * hips down to the lower ankle, over the torso length (so distance to the camera does not matter), relative to the
 * highest value seen since the counter started (standing tall). Unlike the knee angle this reads the same from the
 * front, the side and the diagonal: a knee bending toward the camera looks straight in a 2D image.
 *
 * A rep is a dip and a recovery measured from the cycle's own high point, not from standing: the hips drop at least
 * [drop] (fraction of standing hip height) below the last high point, then rise at least [rise] above the lowest
 * point. That works both for reverse lunges (back to standing each time) and split squats (the high point between
 * reps is the split stance, ~0.8 of standing). Rendered test videos: lunges dip 0.30–0.50, split squats ~0.19,
 * marching on the spot at most 0.07. A cycle faster than [minRepMs] is ignored. Only while the torso is fairly
 * upright, so bending over is never counted. Form rule, side-on only: the torso leans more than [maxLean] from
 * vertical in most frames near the lowest point.
 */
class LungeRepCounter(
    private val drop: Double = 0.12,
    private val rise: Double = 0.12,
    private val minRepMs: Long = 700,
    private val maxUprightTilt: Double = 50.0,
    private val maxLean: Double = 30.0,
    private val minVisibility: Float = 0.6f,
    private val smoothingWindow: Int = 3,
    private val minRuleFrames: Int = 3,
    private val ruleFraction: Double = 0.6,
) : RepCounter {
    private var count = 0
    private var phase = RepPhase.UNKNOWN
    private var standing: Double? = null
    private var peak = 0.0
    private var valley = 0.0
    private var cycleStartMs = 0L
    /** This cycle's frames: hip height, and the torso lean when side-on (null otherwise). Judged when the rep ends,
     *  against the final lowest point — the running lowest point would count the whole descent as "bottom". */
    private val cycle = ArrayList<Pair<Double, Double?>>()
    private val window = ArrayDeque<Double>()

    override val repetitions: Int get() = count

    override fun reset() {
        count = 0
        standing = null
        lose()
    }

    private var lastGoodMs = -1L

    private fun lose() {
        lastGoodMs = -1L
        phase = RepPhase.UNKNOWN
        window.clear()
    }

    private fun PoseFrame.seen(vararg l: BodyLandmark) = l.all { this[it].visibility >= minVisibility }

    /** Hip height over torso length, or null when it can't be read or the person is bent over. */
    private fun hipHeight(f: PoseFrame): Double? {
        if (!f.seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val w = f.imageWidth.toDouble(); val h = f.imageHeight.toDouble()
        val sx = (f[BodyLandmark.LEFT_SHOULDER].x + f[BodyLandmark.RIGHT_SHOULDER].x) / 2.0 * w
        val sy = (f[BodyLandmark.LEFT_SHOULDER].y + f[BodyLandmark.RIGHT_SHOULDER].y) / 2.0 * h
        val hx = (f[BodyLandmark.LEFT_HIP].x + f[BodyLandmark.RIGHT_HIP].x) / 2.0 * w
        val hy = (f[BodyLandmark.LEFT_HIP].y + f[BodyLandmark.RIGHT_HIP].y) / 2.0 * h
        val torso = hypot(sx - hx, sy - hy)
        if (torso < 5.0 || hy <= sy) return null
        if (Math.toDegrees(atan2(abs(sx - hx), hy - sy)) > maxUprightTilt) return null
        val ankle = listOf(BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE).filter { f.seen(it) }.maxOfOrNull { f[it].y * h } ?: return null
        return (ankle - hy) / torso
    }

    override fun update(frame: PoseFrame, tracking: Boolean): RepUpdate {
        val raw = if (tracking) hipHeight(frame) else null
        if (raw == null || raw <= 0.0) {
            if (lastGoodMs >= 0 && frame.timestampMs - lastGoodMs <= MAX_BLIP_MS) return RepUpdate(count, phase, null)
            lose()
            return RepUpdate(count, phase, null)
        }
        lastGoodMs = frame.timestampMs
        window.addLast(raw)
        while (window.size > smoothingWindow) window.removeFirst()
        val r = window.average()
        val base = maxOf(standing ?: r, r).also { standing = it }
        val x = r / base
        val t = frame.timestampMs
        var event: RepEvent? = null
        when (phase) {
            RepPhase.UNKNOWN -> { phase = RepPhase.TOP; peak = x }
            RepPhase.TOP -> {
                peak = maxOf(peak, x)
                if (x < peak - drop) {
                    phase = RepPhase.BOTTOM; valley = x; cycleStartMs = t; cycle.clear()
                }
            }
            RepPhase.DESCENDING, RepPhase.BOTTOM -> {
                valley = minOf(valley, x)
                cycle.add(x to sideLean(frame))
                if (x > valley + rise) {
                    if (t - cycleStartMs >= minRepMs) {
                        count++
                        val bottom = cycle.filter { it.first <= valley + BOTTOM_BAND }.mapNotNull { it.second }
                        val leaning = bottom.size >= minRuleFrames && bottom.count { it > maxLean } >= ruleFraction * bottom.size
                        event = RepEvent.RepCompleted(count, if (leaning) setOf<FormCue>(LungeIssue.LEANING) else emptySet())
                    }
                    phase = RepPhase.TOP; peak = x
                }
            }
        }
        return RepUpdate(count, phase, x, event)
    }

    /** Torso lean from vertical (degrees) when filmed side-on, else null (the lean can't be read head-on). */
    private fun sideLean(f: PoseFrame): Double? {
        if (!f.seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val w = f.imageWidth.toDouble(); val h = f.imageHeight.toDouble()
        fun d(a: BodyLandmark, b: BodyLandmark) = hypot((f[a].x - f[b].x) * w, (f[a].y - f[b].y) * h)
        val torso = (d(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_HIP) + d(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_HIP)) / 2
        if (torso < 5.0 || d(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER) / torso > 0.45) return null
        val sx = (f[BodyLandmark.LEFT_SHOULDER].x + f[BodyLandmark.RIGHT_SHOULDER].x) / 2.0 * w
        val sy = (f[BodyLandmark.LEFT_SHOULDER].y + f[BodyLandmark.RIGHT_SHOULDER].y) / 2.0 * h
        val hx = (f[BodyLandmark.LEFT_HIP].x + f[BodyLandmark.RIGHT_HIP].x) / 2.0 * w
        val hy = (f[BodyLandmark.LEFT_HIP].y + f[BodyLandmark.RIGHT_HIP].y) / 2.0 * h
        return Math.toDegrees(atan2(abs(sx - hx), hy - sy))
    }

    private companion object {
        /** Frames within this much of the cycle's lowest hip height count as the bottom of the lunge. */
        const val BOTTOM_BAND = 0.05
    }
}
