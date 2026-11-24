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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import eu.motionforge.app.feature.session.SessionSnapshot
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.feature.catalog.CatalogUiState
import eu.motionforge.app.feature.catalog.CatalogViewModel
import eu.motionforge.app.feature.progress.ProgressStats
import eu.motionforge.app.feature.session.SessionPlanner
import eu.motionforge.app.feature.session.SessionScreen
import eu.motionforge.app.feature.session.SessionViewModel
import java.time.LocalDate
import java.time.ZoneId
import eu.motionforge.app.feature.catalog.TrainScreen
import eu.motionforge.app.feature.home.HomeScreen
import eu.motionforge.app.feature.lesson.LessonDetailScreen
import eu.motionforge.app.feature.progress.ProgressScreen
import eu.motionforge.app.feature.settings.ProfileScreen
import eu.motionforge.app.feature.spikes.CameraPoseSpikeScreen
import eu.motionforge.app.feature.spikes.GlbSpikeScreen
import eu.motionforge.app.feature.spikes.SpikesScreen

object Routes {
    const val HOME = "home"
    const val TRAIN = "train"
    const val PROGRESS = "progress"
    const val PROFILE = "profile"
    const val LESSON = "lesson/{id}"
    const val SESSION = "session/{plan}"
    const val SPIKES = "spikes"
    const val SPIKE_CAMERA_POSE = "spikes/camera-pose"
    const val SPIKE_GLB = "spikes/glb"

    fun lesson(id: String) = "lesson/$id"
    fun quickSession() = "session/quick"
    fun lessonSession(id: String) = "session/lesson-$id"
    fun session(planKey: String) = "session/$planKey"
}

private data class TopLevelDestination(val route: String, val label: String, val icon: ImageVector)

private val topLevel = listOf(
    TopLevelDestination(Routes.HOME, "Today", Icons.Filled.Home),
    TopLevelDestination(Routes.TRAIN, "Moves", Icons.Filled.PlayArrow),
    TopLevelDestination(Routes.PROFILE, "You", Icons.Filled.Person),
)

private fun NavHostController.navigateTopLevel(route: String) = navigate(route) {
    popUpTo(graph.findStartDestination().id) { saveState = true }
    launchSingleTop = true
    restoreState = true
}

@Composable
fun MotionForgeApp(
    preferences: UserPreferences,
    session: Int,
    container: AppContainer,
    onResetData: () -> Unit,
    navController: NavHostController = rememberNavController(),
) {
    val catalogViewModel: CatalogViewModel = viewModel(key = "catalog-$session") {
        CatalogViewModel(container.exercises, container.preferences)
    }
    val catalog by catalogViewModel.catalog.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    val filter by catalogViewModel.filter.collectAsStateWithLifecycle()

    val activePlan = eu.motionforge.app.feature.plan.TrainingPlans.byId(preferences.activePlanId)
    val history by container.sessions.history.collectAsStateWithLifecycle(initialValue = null)
    val weekSummary = history?.let { ProgressStats.summarize(it, LocalDate.now(), ZoneId.systemDefault()) }
    val sessionsThisWeek = weekSummary?.sessionsThisWeek

    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val showBottomBar = topLevel.any { it.route == currentRoute }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            if (showBottomBar) {
                androidx.compose.foundation.layout.Column {
                    eu.motionforge.app.core.design.ThinRule()
                    NavigationBar(containerColor = MaterialTheme.colorScheme.background, tonalElevation = androidx.compose.ui.unit.Dp(0f)) {
                        topLevel.forEach { dest ->
                            NavigationBarItem(
                                selected = currentRoute == dest.route,
                                onClick = { navController.navigateTopLevel(dest.route) },
                                icon = { Icon(dest.icon, contentDescription = null) },
                                label = { Text(dest.label, style = MaterialTheme.typography.labelLarge) },
                                colors = androidx.compose.material3.NavigationBarItemDefaults.colors(
                                    selectedIconColor = eu.motionforge.app.core.design.MfColors.Ink,
                                    selectedTextColor = eu.motionforge.app.core.design.MfColors.Ink,
                                    indicatorColor = eu.motionforge.app.core.design.MfColors.Yellow,
                                    unselectedIconColor = eu.motionforge.app.core.design.MfColors.Slate,
                                    unselectedTextColor = eu.motionforge.app.core.design.MfColors.Slate,
                                ),
                            )
                        }
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.HOME,
            modifier = Modifier.padding(padding),
            // the default cross-fade shows both screens on top of each other; the new screen fades in over a
            // cleared background instead
            enterTransition = { fadeIn(tween(170)) },
            exitTransition = { ExitTransition.None },
            popEnterTransition = { fadeIn(tween(170)) },
            popExitTransition = { ExitTransition.None },
        ) {
            composable(Routes.HOME) {
                // An unfinished workout (the app was closed mid-session) is offered on Home; re-read on each visit.
                var unfinished by remember { mutableStateOf<SessionSnapshot?>(null) }
                LaunchedEffect(Unit) { unfinished = withContext(Dispatchers.IO) { container.activeSession.read() } }
                HomeScreen(
                    preferences = preferences,
                    catalog = catalog,
                    onOpenLesson = { navController.navigate(Routes.lesson(it)) },
                    onOpenCategory = { category ->
                        catalogViewModel.setCategory(category)
                        navController.navigateTopLevel(Routes.TRAIN)
                    },
                    onStartQuickSession = {
                        container.activeSession.clear()
                        navController.navigate(Routes.quickSession())
                    },
                    unfinished = unfinished,
                    onResumeUnfinished = { navController.navigate(Routes.session(it.planKey)) },
                    onDiscardUnfinished = {
                        container.activeSession.clear()
                        unfinished = null
                    },
                    sessionsThisWeek = sessionsThisWeek,
                    trainedDaysThisWeek = weekSummary?.trainedDaysThisWeek.orEmpty(),
                    onRetry = catalogViewModel::load,
                    activePlan = activePlan,
                    planSession = activePlan?.takeIf { preferences.planSessionsDone < it.totalSessions }?.let { p ->
                        (catalog as? CatalogUiState.Ready)?.let { c ->
                            eu.motionforge.app.feature.plan.PlanSessions.build(p, preferences.planSessionsDone, c.exercises, history.orEmpty())
                        }
                    },
                    onStartPlanSession = {
                        activePlan?.let { p ->
                            container.activeSession.clear()
                            navController.navigate(Routes.session(eu.motionforge.app.feature.plan.TrainingPlans.key(p, preferences.planSessionsDone)))
                        }
                    },
                    onChoosePlan = { id -> scope.launch { container.preferences.startPlan(id) } },
                    onLeavePlan = { scope.launch { container.preferences.leavePlan() } },
                )
            }
            composable(Routes.TRAIN) {
                TrainScreen(
                    catalog = catalog,
                    coach = preferences.coach,
                    filter = filter,
                    onCategory = catalogViewModel::setCategory,
                    onDuration = catalogViewModel::setDuration,
                    onEquipment = catalogViewModel::setEquipment,
                    onClearFilters = catalogViewModel::clearFilters,
                    onQuery = catalogViewModel::setQuery,
                    onOpenLesson = { navController.navigate(Routes.lesson(it)) },
                    onRetry = catalogViewModel::load,
                )
            }
            composable(Routes.PROGRESS) {
                // older links to Progress land on You
                LaunchedEffect(Unit) { navController.navigateTopLevel(Routes.PROFILE) }
            }
            composable(Routes.PROFILE) {
                eu.motionforge.app.feature.settings.YouScreen(
                    history = history,
                    preferences = preferences,
                    coach = preferences.coach,
                    onStartSession = {
                        container.activeSession.clear()
                        navController.navigate(Routes.quickSession())
                    },
                    onOpenTechnicalChecks = { navController.navigate(Routes.SPIKES) },
                    onResetData = onResetData,
                )
            }
            composable(
                Routes.LESSON,
                arguments = listOf(navArgument("id") { type = NavType.StringType }),
            ) { entry ->
                LessonDetailScreen(
                    lessonId = entry.arguments?.getString("id").orEmpty(),
                    catalog = catalog,
                    onBack = { navController.popBackStack() },
                    onViewed = catalogViewModel::markViewed,
                    onStartPractice = {
                        container.activeSession.clear()
                        navController.navigate(Routes.lessonSession(it))
                    },
                    onRetry = catalogViewModel::load,
                )
            }
            composable(
                Routes.SESSION,
                arguments = listOf(navArgument("plan") { type = NavType.StringType }),
            ) { entry ->
                val planArg = entry.arguments?.getString("plan").orEmpty()
                val ready = catalog as? CatalogUiState.Ready
                val planned = eu.motionforge.app.feature.plan.TrainingPlans.parseKey(planArg)
                // targets are fixed when the session opens: saving it must not change the steps under the screen
                val planHistory = remember(planArg) { history.orEmpty() }
                val plan = ready?.let { c ->
                    if (planArg == "quick") {
                        SessionPlanner.quick(c.exercises, preferences.focus)
                    } else if (planned != null) {
                        eu.motionforge.app.feature.plan.PlanSessions.build(planned.first, planned.second, c.exercises, planHistory)
                    } else {
                        c.exercises.firstOrNull { it.id == planArg.removePrefix("lesson-") }?.let(SessionPlanner::single)
                    }
                }
                if (ready == null || plan == null) {
                    ScreenColumn(title = "Session", onBack = { navController.popBackStack() }) {
                        Text(if (catalog is CatalogUiState.Loading) "Loading…" else "This session isn't available.")
                    }
                } else {
                    val sessionViewModel: SessionViewModel = viewModel(key = "session-$planArg") {
                        // Android may have closed the app mid-workout and reopened this screen: carry on from disk.
                        val restored = container.activeSession.read()?.takeIf { it.planKey == planArg }
                        SessionViewModel(
                            plan, container.sessions, container.activeSession, planArg, restored,
                            tips = ready.exercises.associate { it.id to it.commonCues },
                            onSaved = {
                                planned?.let { (p, i) -> container.preferences.markPlanSessionDone(p.id, i) }
                            },
                        )
                    }
                    SessionScreen(
                        viewModel = sessionViewModel,
                        exercisesById = ready.exercises.associateBy { it.id },
                        coach = preferences.coach,
                        voiceCues = preferences.voiceCues,
                        onVoiceCuesChange = { on -> scope.launch { container.preferences.setVoiceCues(on) } },
                        onClose = { navController.popBackStack() },
                        onOpenProgress = {
                            navController.popBackStack()
                            navController.navigateTopLevel(Routes.PROFILE)
                        },
                    )
                }
            }
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
