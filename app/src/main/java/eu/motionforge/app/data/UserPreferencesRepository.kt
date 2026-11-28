package eu.motionforge.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

/**
 * Local-only user settings. Deliberately minimal: no age, no body data, no health data.
 * The age answer from onboarding is never stored — only that onboarding was completed.
 */
data class UserPreferences(
    val onboardingComplete: Boolean,
    val focus: TrainingCategory?,
    val goal: TrainingGoal?,
    val lastViewedExerciseId: String?,
    val coach: Coach = Coach.DEFAULT,
    /** Spoken coaching cues during sessions (on-device text-to-speech). */
    val voiceCues: Boolean = true,
    /** The training plan being followed (TrainingPlans id), or null. */
    val activePlanId: String? = null,
    /** Plan sessions finished so far: the next one is this index. */
    val planSessionsDone: Int = 0,
    /** Optional training reminder (off by default): on/off, the days and the time of day. */
    val reminderOn: Boolean = false,
    /** App language: an I18n code, or "" for the phone's language. */
    val language: String = "",
    val reminder: eu.motionforge.app.feature.reminders.ReminderSchedule = eu.motionforge.app.feature.reminders.ReminderSchedule.DEFAULT,
    /** Sessions a week the person aims for (1–7); the calm weekly streak counts weeks that reach it. */
    val weeklyGoal: Int = eu.motionforge.app.feature.progress.Milestones.DEFAULT_GOAL,
    /** Show the weekly goal, streak and badges (on by default, can be turned off). */
    val milestones: Boolean = true,
    /** Challenges joined (opt-in), with when each was joined. */
    val challenges: List<eu.motionforge.app.feature.progress.JoinedChallenge> = emptyList(),
    /** Add each saved session to Health Connect as a workout (off by default; needs its write permission). */
    val healthConnect: Boolean = false,
)

private val Context.userDataStore: DataStore<Preferences> by preferencesDataStore(name = "user_preferences")

class UserPreferencesRepository(context: Context) {

    private val store = context.applicationContext.userDataStore

    val preferences: Flow<UserPreferences> = store.data
        .catch { e -> if (e is IOException) emit(emptyPreferences()) else throw e }
        .map { p ->
            UserPreferences(
                onboardingComplete = p[ONBOARDING_COMPLETE] ?: false,
                focus = p[FOCUS]?.let { name -> TrainingCategory.entries.firstOrNull { it.name == name } },
                goal = p[GOAL]?.let { name -> TrainingGoal.entries.firstOrNull { it.name == name } },
                lastViewedExerciseId = p[LAST_VIEWED],
                coach = Coach.fromName(p[COACH]),
                voiceCues = p[VOICE_CUES] ?: true,
                activePlanId = p[ACTIVE_PLAN],
                planSessionsDone = p[PLAN_DONE] ?: 0,
                reminderOn = p[REMINDER_ON] ?: false,
                language = p[LANGUAGE] ?: "",
                reminder = eu.motionforge.app.feature.reminders.ReminderSchedule(
                    eu.motionforge.app.feature.reminders.ReminderSchedule.parseDays(p[REMINDER_DAYS])
                        ?: eu.motionforge.app.feature.reminders.ReminderSchedule.DEFAULT.days,
                    (p[REMINDER_MINUTE] ?: eu.motionforge.app.feature.reminders.ReminderSchedule.DEFAULT.minuteOfDay).coerceIn(0, 24 * 60 - 1),
                ),
                weeklyGoal = (p[WEEKLY_GOAL] ?: eu.motionforge.app.feature.progress.Milestones.DEFAULT_GOAL)
                    .coerceIn(eu.motionforge.app.feature.progress.Milestones.GOAL_RANGE),
                milestones = p[MILESTONES] ?: true,
                challenges = eu.motionforge.app.feature.progress.Challenges.decode(p[CHALLENGES]),
                healthConnect = p[HEALTH_CONNECT] ?: false,
            )
        }

    suspend fun completeOnboarding(focus: TrainingCategory, goal: TrainingGoal) {
        store.edit {
            it[ONBOARDING_COMPLETE] = true
            it[FOCUS] = focus.name
            it[GOAL] = goal.name
        }
    }

    suspend fun setLastViewedExercise(id: String) {
        store.edit { it[LAST_VIEWED] = id }
    }

    suspend fun setCoach(coach: Coach) {
        store.edit { it[COACH] = coach.name }
    }

    suspend fun setVoiceCues(on: Boolean) {
        store.edit { it[VOICE_CUES] = on }
    }

    /** Start (or restart) a training plan from its first session. */
    suspend fun startPlan(planId: String) {
        store.edit { it[ACTIVE_PLAN] = planId; it[PLAN_DONE] = 0 }
    }

    suspend fun leavePlan() {
        store.edit { it.remove(ACTIVE_PLAN); it.remove(PLAN_DONE) }
    }

    /** Plan session [index] was saved: the plan moves on (never backwards, never past a session twice). */
    suspend fun markPlanSessionDone(planId: String, index: Int) {
        store.edit {
            if (it[ACTIVE_PLAN] == planId) it[PLAN_DONE] = maxOf(it[PLAN_DONE] ?: 0, index + 1)
        }
    }

    suspend fun setReminder(on: Boolean, schedule: eu.motionforge.app.feature.reminders.ReminderSchedule) {
        store.edit {
            it[REMINDER_ON] = on
            it[REMINDER_DAYS] = schedule.daysWire()
            it[REMINDER_MINUTE] = schedule.minuteOfDay
        }
    }

    suspend fun setWeeklyGoal(goal: Int) {
        store.edit { it[WEEKLY_GOAL] = goal.coerceIn(eu.motionforge.app.feature.progress.Milestones.GOAL_RANGE) }
    }

    suspend fun setMilestones(on: Boolean) {
        store.edit { it[MILESTONES] = on }
    }

    suspend fun setChallenges(list: List<eu.motionforge.app.feature.progress.JoinedChallenge>) {
        store.edit { it[CHALLENGES] = eu.motionforge.app.feature.progress.Challenges.encode(list) }
    }

    suspend fun setHealthConnect(on: Boolean) {
        store.edit { it[HEALTH_CONNECT] = on }
    }

    suspend fun setLanguage(code: String) {
        store.edit { it[LANGUAGE] = code }
    }

    /** Local data reset: removes every stored preference and returns the app to onboarding. */
    suspend fun clearAll() {
        store.edit { it.clear() }
    }

    private companion object {
        val ONBOARDING_COMPLETE = booleanPreferencesKey("onboarding_complete")
        val FOCUS = stringPreferencesKey("focus")
        val GOAL = stringPreferencesKey("goal")
        val LAST_VIEWED = stringPreferencesKey("last_viewed_exercise")
        val COACH = stringPreferencesKey("coach")
        val VOICE_CUES = booleanPreferencesKey("voice_cues")
        val ACTIVE_PLAN = stringPreferencesKey("active_plan")
        val PLAN_DONE = androidx.datastore.preferences.core.intPreferencesKey("plan_sessions_done")
        val REMINDER_ON = booleanPreferencesKey("reminder_on")
        val LANGUAGE = stringPreferencesKey("language")
        val REMINDER_DAYS = stringPreferencesKey("reminder_days")
        val REMINDER_MINUTE = androidx.datastore.preferences.core.intPreferencesKey("reminder_minute")
        val WEEKLY_GOAL = androidx.datastore.preferences.core.intPreferencesKey("weekly_goal")
        val MILESTONES = booleanPreferencesKey("milestones")
        val CHALLENGES = stringPreferencesKey("challenges")
        val HEALTH_CONNECT = booleanPreferencesKey("health_connect")
    }
}
