package eu.motionforge.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import eu.motionforge.app.core.design.MotionForgeTheme
import eu.motionforge.app.feature.onboarding.OnboardingScreen
import eu.motionforge.app.feature.onboarding.OnboardingViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MotionForgeTheme {
                MotionForgeRoot()
            }
        }
    }
}

/** Decides between onboarding and the main app based on locally stored preferences. */
@Composable
fun MotionForgeRoot() {
    val container = (LocalContext.current.applicationContext as MotionForgeApplication).container
    val appViewModel: AppViewModel = viewModel { AppViewModel(container.preferences, container.sessions, container.activeSession) }
    val state by appViewModel.state.collectAsStateWithLifecycle()

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        when (val s = state) {
            AppUiState.Loading -> Unit // brief; preferences are local
            is AppUiState.NeedsOnboarding -> {
                val vm: OnboardingViewModel = viewModel(key = "onboarding-${s.session}") {
                    OnboardingViewModel(container.preferences)
                }
                OnboardingScreen(vm)
            }
            is AppUiState.Ready -> MotionForgeApp(
                preferences = s.preferences,
                session = s.session,
                container = container,
                onResetData = appViewModel::resetAllData,
            )
        }
    }
}
