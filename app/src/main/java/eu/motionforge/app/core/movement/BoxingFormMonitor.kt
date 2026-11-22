package eu.motionforge.app.core.movement

import eu.motionforge.app.core.pose.BodyLandmark
import eu.motionforge.app.core.pose.Landmark
import eu.motionforge.app.core.pose.PoseFrame
import kotlin.math.hypot

/** Which beginner boxing drill is being watched. CROSS uses the jab rules on the rear hand: the punching arm is
 *  whichever arm extends at shoulder height, and the other hand must stay up. */
enum class BoxingDrill { STANCE, JAB, CROSS }

/** [message] is shown on screen, [spoken] is the short version the voice coach says. */
enum class FormIssue(val message: String, val spoken: String) {
    HANDS_LOW("Possible form adjustment: bring your hands up near your face.", "Hands up by your face."),
    FEET_NARROW("Possible form adjustment: step your feet a little wider for balance.", "Feet a little wider."),
    FEET_WIDE("Your feet may be very wide — find a comfortable, balanced width.", "Feet a little narrower."),
    REAR_HAND_DROPS("Possible form adjustment: keep the rear hand near your face while the lead hand extends.", "Keep the rear hand up."),
    LEAD_HAND_DROPS("Possible form adjustment: keep the lead hand near your face while the rear hand extends.", "Keep the lead hand up."),
    SLOW_RETURN("Possible form adjustment: bring the hand back to guard after each jab.", "Bring it back to guard."),
}

/**
 * One finished jab (extended, then back to guard). [clean] = it came back within the return time and the rear
 * hand stayed up the whole time. Says nothing about power, speed or accuracy.
 */
data class JabResult(val number: Int, val clean: Boolean)

/**
 * What the monitor reports.
 * - [NotAssessing]: the needed landmarks are not clearly visible (or tracking is off). Never gives advice then.
 * - [Steady]: visible and no rule has been met for long enough.
 * - [Cue]: one rule has held for most of the recent window; shown for at least [BoxingFormMonitor.holdMs].
 */
sealed interface FormFeedback {
    val jabs: Int

    data class NotAssessing(override val jabs: Int) : FormFeedback
    data class Steady(override val jabs: Int) : FormFeedback
    data class Cue(val issue: FormIssue, override val jabs: Int) : FormFeedback
}

/**
 * Rule-based, explainable feedback for the boxing stance and the jab, from 2D pose landmarks.
 *
 * Every rule is a simple geometric test in pixel space, normalised by the shoulder width so that distance to
 * the camera does not matter. A rule only becomes a cue when it is true in at least [persistFraction] of the
 * frames of the last [windowMs]; a single low-quality frame can never produce advice. Low-visibility frames are
 * skipped and, if they dominate, the state is [FormFeedback.NotAssessing].
 *
 * Thresholds are first hypotheses for coach review and device testing — not biomechanical truths. The monitor
 * never judges power, speed, impact or injury risk.
 */
class BoxingFormMonitor(
    private val drill: BoxingDrill,
    private val minVisibility: Float = 0.6f,
    private val windowMs: Long = 1_000,
    private val persistFraction: Double = 0.7,
    val holdMs: Long = 2_500,
    private val handsLowBelowShoulder: Double = 0.15,
    private val feetNarrow: Double = 0.75,
    private val feetWide: Double = 2.1,
    private val extendedRatio: Double = 0.60,
    private val guardRatio: Double = 0.50,
    /** An extended arm only counts as a jab with the hand around shoulder height (not hanging by the side). */
    private val jabHeight: Double = 0.6,
    private val returnMs: Long = 1_500,
    private val minJabMs: Long = 400,
    private val minFrontalRatio: Double = 0.40,
) {
    private data class Sample(val t: Long, val issues: Set<FormIssue>)

    private val window = ArrayDeque<Sample>()
    private var visibleFrames = 0
    private var hiddenFrames = 0
    private var shown: FormIssue? = null
    private var shownSince = 0L
    private var jabCount = 0
    private var extended = false
    private var extendedAt = 0L
    private var lastJabAt = -1_000_000L
    private var rearDroppedThisJab = false
    private var extendedLeft = true
    private var pendingCue: FormIssue? = null
    /** The hand that must stay up while the other punches: the rear hand for a jab, the lead hand for a cross. */
    private val guardCue = if (drill == BoxingDrill.CROSS) FormIssue.LEAD_HAND_DROPS else FormIssue.REAR_HAND_DROPS
    private var slowThisJab = false
    private var cleanJabs = 0
    private val finished = ArrayDeque<JabResult>()

    val jabs: Int get() = jabCount

    /** Jabs that came back to guard in time with the rear hand up. */
    val goodJabs: Int get() = cleanJabs

    /** Jabs finished since the last call, oldest first. */
    fun drainJabs(): List<JabResult> = finished.toList().also { finished.clear() }

    fun reset() {
        window.clear(); visibleFrames = 0; hiddenFrames = 0; shown = null; extended = false; pendingCue = null; rearDroppedThisJab = false; slowThisJab = false; finished.clear()
    }

    fun update(frame: PoseFrame, tracking: Boolean): FormFeedback {
        val t = frame.timestampMs
        val issues = if (tracking) evaluate(frame) else null
        if (issues == null) {
            hiddenFrames++
            window.addLast(Sample(t, emptySet()).copy())
            trim(t)
            // mostly unseen recently -> stop advising
            if (hiddenFrames > visibleFrames) {
                shown = null; extended = false
                return FormFeedback.NotAssessing(jabCount)
            }
        } else {
            visibleFrames++
            window.addLast(Sample(t, issues))
            trim(t)
        }
        pendingCue?.let { cue ->
            pendingCue = null
            shown = cue; shownSince = t
            return FormFeedback.Cue(cue, jabCount)
        }
        if (window.size < 5) return FormFeedback.Steady(jabCount)

        val current = shown
        if (current != null && t - shownSince < holdMs) return FormFeedback.Cue(current, jabCount)
        val persistent = FormIssue.entries.firstOrNull { issue ->
            window.count { issue in it.issues } >= persistFraction * window.size
        }
        if (persistent != null && persistent != current) {
            shown = persistent; shownSince = t
        } else if (persistent == null) {
            shown = null
        }
        return shown?.let { FormFeedback.Cue(it, jabCount) } ?: FormFeedback.Steady(jabCount)
    }

    private fun trim(t: Long) {
        while (window.isNotEmpty() && t - window.first().t > windowMs) {
            window.removeFirst()
        }
        if (visibleFrames + hiddenFrames > 60) { visibleFrames /= 2; hiddenFrames /= 2 }
    }

    /** Issues seen in this frame, or null when the frame cannot be assessed. */
    private fun frontalEnough(f: PoseFrame, shoulderWidthPx: Double, dist: (Landmark, Landmark) -> Double): Boolean {
        val lh = f[BodyLandmark.LEFT_HIP]; val rh = f[BodyLandmark.RIGHT_HIP]
        if (lh.visibility < minVisibility || rh.visibility < minVisibility) return false
        val ls = f[BodyLandmark.LEFT_SHOULDER]; val rs = f[BodyLandmark.RIGHT_SHOULDER]
        val torso = (dist(ls, lh) + dist(rs, rh)) / 2
        return torso > 1.0 && shoulderWidthPx / torso >= minFrontalRatio
    }

    private fun evaluate(f: PoseFrame): Set<FormIssue>? {
        fun seen(vararg l: BodyLandmark) = l.all { f[it].visibility >= minVisibility }
        // the torso must be seen; arms and feet are each used only when visible (a bladed stance filmed from the
        // diagonal hides the rear arm and the far foot behind the body)
        if (!seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.RIGHT_SHOULDER, BodyLandmark.LEFT_HIP, BodyLandmark.RIGHT_HIP)) return null
        val w = f.imageWidth.toDouble()
        val h = f.imageHeight.toDouble()
        fun px(l: Landmark) = (l.x * w) to (l.y * h)
        fun dist(a: Landmark, b: Landmark): Double {
            val (ax, ay) = px(a); val (bx, by) = px(b); return hypot(ax - bx, ay - by)
        }
        val ls = f[BodyLandmark.LEFT_SHOULDER]; val rs = f[BodyLandmark.RIGHT_SHOULDER]
        val sw = dist(ls, rs)
        val torso = (dist(ls, f[BodyLandmark.LEFT_HIP]) + dist(rs, f[BodyLandmark.RIGHT_HIP])) / 2
        // Distances are measured in "shoulder widths". Seen from the front that is the real shoulder width; when the
        // body turns, the shoulders shrink in the image but the torso does not, so the unit falls back to the
        // shoulder width a front view would show for this torso.
        val unit = maxOf(sw, FRONTAL_SHOULDERS_PER_TORSO * torso)
        if (unit < 20.0) return null                                 // too far away to read
        val shoulderY = (ls.y + rs.y) / 2 * h
        val issues = mutableSetOf<FormIssue>()
        val leftArm = seen(BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_ELBOW, BodyLandmark.LEFT_WRIST)
        val rightArm = seen(BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_ELBOW, BodyLandmark.RIGHT_WRIST)

        fun wristLow(wrist: Landmark) = wrist.y * h > shoulderY + handsLowBelowShoulder * unit
        fun reachRatio(side: String): Double {
            val s = f[if (side == "L") BodyLandmark.LEFT_SHOULDER else BodyLandmark.RIGHT_SHOULDER]
            val e = f[if (side == "L") BodyLandmark.LEFT_ELBOW else BodyLandmark.RIGHT_ELBOW]
            val wr = f[if (side == "L") BodyLandmark.LEFT_WRIST else BodyLandmark.RIGHT_WRIST]
            val chain = dist(s, e) + dist(e, wr)
            return if (chain < 1.0) 0.0 else dist(s, wr) / chain
        }

        // Foot spacing can only be read when the camera sees the body roughly from the front. A bladed stance seen from
        // the diagonal lines the feet up behind each other and shrinks the shoulder width, which would look "narrow"
        // although the stance is fine. The torso length does not shrink when the body turns, so shoulders that are
        // short compared with the torso mean "turned away": skip the feet rules instead of guessing.
        if (seen(BodyLandmark.LEFT_ANKLE, BodyLandmark.RIGHT_ANKLE) && frontalEnough(f, sw, ::dist)) {
            val feet = dist(f[BodyLandmark.LEFT_ANKLE], f[BodyLandmark.RIGHT_ANKLE]) / sw
            if (feet < feetNarrow) issues += FormIssue.FEET_NARROW
            if (feet > feetWide) issues += FormIssue.FEET_WIDE
        }

        val lw = f[BodyLandmark.LEFT_WRIST]; val rw = f[BodyLandmark.RIGHT_WRIST]
        when (drill) {
            BoxingDrill.STANCE -> {
                if (!leftArm || !rightArm) return null                 // the guard needs both hands in view
                if (wristLow(lw) && wristLow(rw)) issues += FormIssue.HANDS_LOW
            }
            BoxingDrill.JAB, BoxingDrill.CROSS -> {
                if (!leftArm && !rightArm) return null
                fun high(wr: Landmark) = wr.y * h < shoulderY + jabHeight * unit
                val rl = if (leftArm) reachRatio("L") else -1.0
                val rr = if (rightArm) reachRatio("R") else -1.0
                // The punching arm is the straighter arm *at shoulder height*: a dropped rear hand hangs straight too,
                // and must not be taken for the jab. While a jab is out, keep watching the arm that threw it.
                val leadIsLeft = if (extended) extendedLeft else {
                    val lHigh = leftArm && high(lw); val rHigh = rightArm && high(rw)
                    when {
                        lHigh && rHigh -> rl >= rr
                        lHigh -> true
                        rHigh -> false
                        else -> rl >= rr
                    }
                }
                val lead = if (leadIsLeft) rl else rr
                if (lead < 0) return issues                               // the punching arm is hidden this frame
                val rearSeen = if (leadIsLeft) rightArm else leftArm
                val rear = if (leadIsLeft) rw else lw
                val t = f.timestampMs
                val leadWrist = if (leadIsLeft) lw else rw
                if (!extended && lead > extendedRatio && high(leadWrist) && t - lastJabAt > minJabMs) {
                    extended = true; extendedLeft = leadIsLeft; extendedAt = t; jabCount++; lastJabAt = t
                    rearDroppedThisJab = false; slowThisJab = false
                }
                if (extended) {
                    if (rearSeen && wristLow(rear)) rearDroppedThisJab = true
                    if (lead < guardRatio) {
                        extended = false
                        val clean = !rearDroppedThisJab && !slowThisJab
                        if (clean) cleanJabs++
                        finished.addLast(JabResult(jabCount, clean))
                        // a jab lasts well under the cue window, so a fault seen during it is named straight away
                        pendingCue = when {
                            rearDroppedThisJab -> guardCue
                            slowThisJab -> FormIssue.SLOW_RETURN
                            else -> null
                        }
                    } else if (t - extendedAt > returnMs) {
                        issues += FormIssue.SLOW_RETURN; slowThisJab = true
                    }
                }
                if (extended && rearDroppedThisJab) issues += guardCue
                if (!extended && leftArm && rightArm && wristLow(lw) && wristLow(rw)) issues += FormIssue.HANDS_LOW
            }
        }
        return issues
    }

    private companion object {
        /** Shoulder width over torso length of a person facing the camera (0.66–0.70 measured on the rendered test videos). */
        const val FRONTAL_SHOULDERS_PER_TORSO = 0.68
    }
}
