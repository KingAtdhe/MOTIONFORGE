package eu.motionforge.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import eu.motionforge.app.core.design.MotionForgeTheme
import eu.motionforge.app.feature.onboarding.OnboardingScreen
import eu.motionforge.app.feature.onboarding.OnboardingViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen() // launch screen: MOTIONFORGE mark on the night background
        super.onCreate(savedInstanceState)
        // light "gym floor" chrome: dark status/navigation icons whatever the phone's dark-mode setting
        val ground = android.graphics.Color.rgb(0xE8, 0xE8, 0xE4)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.light(ground, ground),
        )
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
    val appContext = LocalContext.current.applicationContext
    val container = (appContext as MotionForgeApplication).container
    val appViewModel: AppViewModel = viewModel { AppViewModel(container.preferences, container.sessions, container.activeSession) }
    val state by appViewModel.state.collectAsStateWithLifecycle()
    // the chosen language (or the phone's): its table loads off the main thread, then the whole UI redraws in it
    val lang = eu.motionforge.app.core.i18n.I18n.resolve((state as? AppUiState.Ready)?.preferences?.language)
    var loaded by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<String?>(null) }
    // English needs no table, so it is ready at once (no blank first frame)
    val applied: String? = if (lang == "en") {
        androidx.compose.runtime.remember(lang) { eu.motionforge.app.core.i18n.I18n.use("en", emptyMap()); "en" }
    } else loaded
    androidx.compose.runtime.LaunchedEffect(lang) {
        if (lang != "en") {
            kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { eu.motionforge.app.core.i18n.I18nLoader.apply(appContext, lang) }
            loaded = lang
        }
    }

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        if (applied == null) return@Box
        androidx.compose.runtime.key(applied) {
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
                onResetData = {
                    eu.motionforge.app.feature.reminders.Reminders.cancel(appContext)
                    appViewModel.resetAllData()
                },
            )
        }
        }
    }
}
