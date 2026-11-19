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
    }
}
