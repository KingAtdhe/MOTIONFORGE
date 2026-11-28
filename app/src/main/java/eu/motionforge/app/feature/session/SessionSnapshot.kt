package eu.motionforge.app.feature.session

import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.movement.BoxingDrill
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import kotlinx.serialization.json.put

/**
 * An unfinished session, written to app-private storage while it runs so it survives Android closing the app.
 * Holds only timer/step/result numbers — never camera data. [planKey] is the navigation argument the session was
 * opened with ("quick", "lesson-<id>"), so the same screen can pick it up again.
 */
data class SessionSnapshot(
    val planKey: String,
    val state: SessionState,
    val startedAtMillis: Long,
    val savedAtMillis: Long,
) {
    /**
     * The state to show when the session is reopened. Time that passed while the app was closed is not counted,
     * so a running session comes back paused (the person decides when to go on).
     */
    fun restoredState(): SessionState =
        if (state.phase == SessionPhase.RUNNING) state.copy(phase = SessionPhase.PAUSED) else state

    fun isExpired(nowMillis: Long): Boolean = nowMillis - savedAtMillis > MAX_AGE_MILLIS || nowMillis < savedAtMillis - CLOCK_SLACK_MILLIS

    companion object {
        const val VERSION = 1
        /** After this long an unfinished session is no longer offered. */
        const val MAX_AGE_MILLIS = 24L * 60 * 60 * 1000
        private const val CLOCK_SLACK_MILLIS = 5L * 60 * 1000

        fun encode(s: SessionSnapshot): String = buildJsonObject {
            put("version", VERSION)
            put("planKey", s.planKey)
            put("startedAt", s.startedAtMillis)
            put("savedAt", s.savedAtMillis)
            val st = s.state
            put("plan", buildJsonObject {
                put("title", st.plan.title)
                put("type", st.plan.type.wireName)
                put("steps", buildJsonArray {
                    st.plan.steps.forEach { step ->
                        add(when (step) {
                            is SessionStep.Work -> buildJsonObject {
                                put("kind", "work")
                                put("exerciseId", step.exerciseId)
                                put("name", step.name)
                                put("seconds", step.durationSeconds)
                                put("countsReps", step.countsReps)
                                step.formDrill?.let { put("formDrill", it.name) }
                                step.holdCheck?.let { put("holdCheck", it.name) }
                                step.targetReps?.let { put("targetReps", it) }
                                step.round?.let { put("round", it) }
                                if (step.calls.isNotEmpty()) {
                                    put("calls", buildJsonArray { step.calls.forEach { add(kotlinx.serialization.json.JsonPrimitive(it)) } })
                                    put("callEvery", step.callEverySeconds)
                                }
                            }
                            is SessionStep.Rest -> buildJsonObject {
                                put("kind", "rest")
                                put("seconds", step.durationSeconds)
                                put("nextName", step.nextName)
                            }
                        })
                    }
                })
            })
            put("cameraUsed", st.cameraUsed)
            put("phase", st.phase.name)
            put("stepIndex", st.stepIndex)
            put("remainingInStep", st.remainingInStep)
            put("elapsedTotal", st.elapsedTotal)
            put("stepElapsed", st.stepElapsed)
            put("stepTracked", st.stepTracked)
            put("stepReps", st.stepReps)
            put("stepHeld", st.stepHeld)
            put("stepFlagged", st.stepFlagged)
            put("stepShallow", st.stepShallow)
            put("endedEarly", st.endedEarly)
            put("results", buildJsonArray {
                st.results.forEach { r ->
                    add(buildJsonObject {
                        put("exerciseId", r.exerciseId)
                        put("name", r.name)
                        put("sequence", r.sequence)
                        put("seconds", r.elapsedSeconds)
                        r.repetitions?.let { put("reps", it) }
                        put("quality", r.trackingQuality.wireName)
                        r.targetReps?.let { put("targetReps", it) }
                        r.heldSeconds?.let { put("held", it) }
                        r.cleanReps?.let { put("clean", it) }
                        r.shallowReps?.let { put("shallow", it) }
                    })
                }
            })
        }.toString()

        /** Null for anything unreadable, from another version, or internally inconsistent. */
        fun decode(text: String): SessionSnapshot? = runCatching {
            val o = Json.parseToJsonElement(text).jsonObject
            require(o.int("version") == VERSION)
            val p = o.getValue("plan").jsonObject
            val steps = p.getValue("steps").jsonArray.map { e ->
                val so = e.jsonObject
                when (so.str("kind")) {
                    "work" -> SessionStep.Work(
                        exerciseId = so.str("exerciseId"),
                        name = so.str("name"),
                        durationSeconds = so.int("seconds"),
                        countsReps = so.getValue("countsReps").jsonPrimitive.boolean,
                        formDrill = so["formDrill"]?.jsonPrimitive?.content?.let { BoxingDrill.valueOf(it) },
                        holdCheck = so["holdCheck"]?.jsonPrimitive?.content?.let { eu.motionforge.app.core.movement.HoldCheck.valueOf(it) },
                        targetReps = so["targetReps"]?.jsonPrimitive?.intOrNull,
                        round = so["round"]?.jsonPrimitive?.intOrNull,
                        calls = so["calls"]?.jsonArray?.map { it.jsonPrimitive.content }.orEmpty(),
                        callEverySeconds = so["callEvery"]?.jsonPrimitive?.intOrNull ?: 0,
                    )
                    "rest" -> SessionStep.Rest(so.int("seconds"), so.str("nextName"))
                    else -> error("unknown step")
                }
            }
            val plan = SessionPlan(
                title = p.str("title"),
                type = TrainingCategory.entries.first { it.wireName == p.str("type") },
                steps = steps,
            )
            val results = o.getValue("results").jsonArray.map { e ->
                val r = e.jsonObject
                StepResult(
                    exerciseId = r.str("exerciseId"),
                    name = r.str("name"),
                    sequence = r.int("sequence"),
                    elapsedSeconds = r.int("seconds"),
                    repetitions = r["reps"]?.jsonPrimitive?.intOrNull,
                    trackingQuality = TrackingQuality.entries.first { it.wireName == r.str("quality") },
                    targetReps = r["targetReps"]?.jsonPrimitive?.intOrNull,
                    heldSeconds = r["held"]?.jsonPrimitive?.intOrNull,
                    cleanReps = r["clean"]?.jsonPrimitive?.intOrNull,
                    shallowReps = r["shallow"]?.jsonPrimitive?.intOrNull,
                )
            }
            val state = SessionState(
                plan = plan,
                cameraUsed = o.getValue("cameraUsed").jsonPrimitive.boolean,
                phase = SessionPhase.valueOf(o.str("phase")),
                stepIndex = o.int("stepIndex"),
                remainingInStep = o.int("remainingInStep"),
                elapsedTotal = o.int("elapsedTotal"),
                stepElapsed = o.int("stepElapsed"),
                stepTracked = o.int("stepTracked"),
                stepReps = o.int("stepReps"),
                stepHeld = o["stepHeld"]?.jsonPrimitive?.intOrNull ?: 0,
                stepFlagged = o["stepFlagged"]?.jsonPrimitive?.intOrNull ?: 0,
                stepShallow = o["stepShallow"]?.jsonPrimitive?.intOrNull ?: 0,
                results = results,
                endedEarly = o.getValue("endedEarly").jsonPrimitive.boolean,
            )
            require(state.stepIndex in plan.steps.indices)
            require(state.remainingInStep in 0..plan.steps[state.stepIndex].durationSeconds)
            require(state.elapsedTotal >= 0 && state.stepElapsed >= 0 && state.stepTracked in 0..state.stepElapsed && state.stepReps >= 0 && state.stepHeld >= 0)
            SessionSnapshot(o.str("planKey"), state, o.getValue("startedAt").jsonPrimitive.long, o.getValue("savedAt").jsonPrimitive.long)
        }.getOrNull()

        private fun JsonObject.str(key: String) = getValue(key).jsonPrimitive.content
        private fun JsonObject.int(key: String) = getValue(key).jsonPrimitive.int
    }
}
