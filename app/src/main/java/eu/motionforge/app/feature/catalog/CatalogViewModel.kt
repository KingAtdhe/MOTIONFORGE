package eu.motionforge.app.feature.catalog

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import eu.motionforge.app.core.model.Exercise
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.data.ExerciseRepository
import eu.motionforge.app.data.UserPreferencesRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface CatalogUiState {
    data object Loading : CatalogUiState
    data class Ready(val exercises: List<Exercise>) : CatalogUiState
    data class Error(val message: String) : CatalogUiState
}

class CatalogViewModel(
    private val exercises: ExerciseRepository,
    private val preferences: UserPreferencesRepository,
) : ViewModel() {

    private val _catalog = MutableStateFlow<CatalogUiState>(CatalogUiState.Loading)
    val catalog: StateFlow<CatalogUiState> = _catalog.asStateFlow()

    private val _filter = MutableStateFlow(CatalogFilter())
    val filter: StateFlow<CatalogFilter> = _filter.asStateFlow()

    init {
        load()
    }

    fun load() {
        _catalog.value = CatalogUiState.Loading
        viewModelScope.launch {
            _catalog.value = exercises.loadCatalog().fold(
                onSuccess = { CatalogUiState.Ready(it) },
                onFailure = { CatalogUiState.Error("The lesson catalogue could not be read. (${it.message})") },
            )
        }
    }

    fun setCategory(category: TrainingCategory?) {
        _filter.value = _filter.value.copy(category = category)
    }

    fun setDuration(duration: DurationFilter) {
        _filter.value = _filter.value.copy(duration = duration)
    }

    fun setEquipment(equipment: EquipmentFilter) {
        _filter.value = _filter.value.copy(equipment = equipment)
    }

    fun setQuery(query: String) {
        _filter.value = _filter.value.copy(query = query.take(60))
    }

    fun clearFilters() {
        _filter.value = CatalogFilter()
    }

    fun markViewed(id: String) {
        viewModelScope.launch { runCatching { preferences.setLastViewedExercise(id) } }
    }
}
