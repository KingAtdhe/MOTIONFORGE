package eu.motionforge.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import eu.motionforge.app.data.SessionRepository
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.data.UserPreferencesRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

sealed interface AppUiState {
    data object Loading : AppUiState

    /** [session] changes after a data reset so per-session ViewModels start fresh. */
    data class NeedsOnboarding(val session: Int) : AppUiState
    data class Ready(val preferences: UserPreferences, val session: Int) : AppUiState
}

class AppViewModel(
    private val preferences: UserPreferencesRepository,
    private val sessions: SessionRepository,
) : ViewModel() {

    private val session = MutableStateFlow(0)

    val state: StateFlow<AppUiState> = combine(preferences.preferences, session) { prefs, s ->
        if (prefs.onboardingComplete) AppUiState.Ready(prefs, s) else AppUiState.NeedsOnboarding(s)
    }.stateIn(viewModelScope, SharingStarted.Eagerly, AppUiState.Loading)

    fun resetAllData() {
        viewModelScope.launch {
            sessions.deleteAll()
            preferences.clearAll()
            session.value += 1
        }
    }
}
