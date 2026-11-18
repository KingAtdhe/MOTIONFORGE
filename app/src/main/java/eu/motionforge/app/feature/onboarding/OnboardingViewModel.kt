package eu.motionforge.app.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import eu.motionforge.app.data.UserPreferencesRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class OnboardingViewModel(private val preferences: UserPreferencesRepository) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingState())
    val state: StateFlow<OnboardingState> = _state.asStateFlow()

    private val _saving = MutableStateFlow(false)
    val saving: StateFlow<Boolean> = _saving.asStateFlow()

    fun onEvent(event: OnboardingEvent) {
        if (_saving.value) return
        val transition = OnboardingReducer.reduce(_state.value, event)
        _state.value = transition.state
        if (transition.completed) {
            val focus = transition.state.focus ?: return
            val goal = transition.state.goal ?: return
            _saving.value = true
            viewModelScope.launch {
                // AppViewModel observes the stored flag and switches to the main app.
                runCatching { preferences.completeOnboarding(focus, goal) }
                _saving.value = false
            }
        }
    }
}
