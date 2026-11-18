package eu.motionforge.app

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import eu.motionforge.app.feature.home.HomeScreen
import eu.motionforge.app.feature.progress.ProgressScreen
import eu.motionforge.app.feature.settings.ProfileScreen
import eu.motionforge.app.feature.catalog.TrainScreen
import eu.motionforge.app.feature.spikes.CameraPoseSpikeScreen
import eu.motionforge.app.feature.spikes.GlbSpikeScreen
import eu.motionforge.app.feature.spikes.SpikesScreen

object Routes {
    const val HOME = "home"
    const val TRAIN = "train"
    const val PROGRESS = "progress"
    const val PROFILE = "profile"
    const val SPIKES = "spikes"
    const val SPIKE_CAMERA_POSE = "spikes/camera-pose"
    const val SPIKE_GLB = "spikes/glb"
}

private data class TopLevelDestination(val route: String, val label: String, val icon: ImageVector)

private val topLevel = listOf(
    TopLevelDestination(Routes.HOME, "Home", Icons.Filled.Home),
    TopLevelDestination(Routes.TRAIN, "Train", Icons.Filled.PlayArrow),
    TopLevelDestination(Routes.PROGRESS, "Progress", Icons.Filled.DateRange),
    TopLevelDestination(Routes.PROFILE, "Profile", Icons.Filled.Person),
)

@Composable
fun MotionForgeApp(navController: NavHostController = rememberNavController()) {
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val showBottomBar = topLevel.any { it.route == currentRoute }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                    topLevel.forEach { dest ->
                        NavigationBarItem(
                            selected = currentRoute == dest.route,
                            onClick = {
                                navController.navigate(dest.route) {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(dest.icon, contentDescription = null) },
                            label = { Text(dest.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.HOME,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.HOME) { HomeScreen(onOpenSpikes = { navController.navigate(Routes.SPIKES) }) }
            composable(Routes.TRAIN) { TrainScreen() }
            composable(Routes.PROGRESS) { ProgressScreen() }
            composable(Routes.PROFILE) { ProfileScreen() }
            composable(Routes.SPIKES) {
                SpikesScreen(
                    onBack = { navController.popBackStack() },
                    onOpenCameraPose = { navController.navigate(Routes.SPIKE_CAMERA_POSE) },
                    onOpenGlb = { navController.navigate(Routes.SPIKE_GLB) },
                )
            }
            composable(Routes.SPIKE_CAMERA_POSE) { CameraPoseSpikeScreen(onBack = { navController.popBackStack() }) }
            composable(Routes.SPIKE_GLB) { GlbSpikeScreen(onBack = { navController.popBackStack() }) }
        }
    }
}
