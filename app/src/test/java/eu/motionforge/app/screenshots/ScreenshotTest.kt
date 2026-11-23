package eu.motionforge.app.screenshots

import android.graphics.Bitmap
import android.graphics.Canvas
import androidx.activity.ComponentActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import eu.motionforge.app.core.design.MotionForgeTheme
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal
import eu.motionforge.app.data.ExerciseCatalogParser
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.catalog.CatalogFilter
import eu.motionforge.app.feature.catalog.CatalogUiState
import eu.motionforge.app.feature.catalog.TrainScreen
import eu.motionforge.app.feature.home.HomeScreen
import eu.motionforge.app.feature.lesson.LessonDetailScreen
import eu.motionforge.app.feature.onboarding.OnboardingContent
import eu.motionforge.app.feature.onboarding.OnboardingState
import eu.motionforge.app.feature.onboarding.OnboardingStep
import eu.motionforge.app.feature.progress.ExerciseRecord
import eu.motionforge.app.feature.progress.ProgressScreen
import eu.motionforge.app.feature.progress.SessionRecord
import eu.motionforge.app.feature.settings.ProfileScreen
import eu.motionforge.app.core.model.Coach
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.shadows.ShadowLooper
import java.io.File
import java.time.DayOfWeek

/**
 * Renders the main screens with sample data to PNGs in build/reports/screenshots/, so the design can be reviewed
 * without a device (CI pushes them to the `ci-screenshots` branch). Not a pixel-comparison test. Runs only when
 * MF_SCREENSHOTS=1, in its own CI step, so it can never block the unit tests or the APK.
 *
 * The frame clock is driven by hand and the window is drawn straight into a bitmap, so a screen that is still loading
 * pictures cannot stall the capture.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w411dp-h1900dp-xhdpi")
class ScreenshotTest {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    @Before fun onlyWhenAsked() = assumeTrue(System.getenv("MF_SCREENSHOTS") == "1")

    private val catalog = CatalogUiState.Ready(
        ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText()),
    )
    private val prefs = UserPreferences(
        onboardingComplete = true, focus = TrainingCategory.FITNESS, goal = TrainingGoal.BUILD_ROUTINE,
        lastViewedExerciseId = "bodyweight_squat",
    )

    private fun shot(name: String, content: @Composable () -> Unit) {
        compose.mainClock.autoAdvance = false
        compose.setContent {
            MotionForgeTheme {
                Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) { content() }
            }
        }
        compose.mainClock.autoAdvance = false
        repeat(10) {
            compose.mainClock.advanceTimeBy(200)
            ShadowLooper.idleMainLooper()
            Thread.sleep(150)                                     // coach stills load on Dispatchers.IO
        }
        val root = compose.activity.window.decorView
        val bmp = Bitmap.createBitmap(root.width, root.height, Bitmap.Config.ARGB_8888)
        root.draw(Canvas(bmp))
        val out = File("build/reports/screenshots").apply { mkdirs() }
        File(out, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test fun home() = shot("01_home") {
        HomeScreen(prefs, catalog, {}, {}, {}, sessionsThisWeek = 2, onRetry = {}, trainedDaysThisWeek = setOf(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY))
    }

    @Test fun homeWithPlan() = shot("12_home_plan") {
        val p = eu.motionforge.app.feature.plan.TrainingPlans.FOUNDATIONS
        val history = listOf(
            SessionRecord(1, "Foundations", TrainingCategory.FITNESS, System.currentTimeMillis() - 86_400_000, 600, 6, true,
                listOf(ExerciseRecord("sumo_squat", "Sumo Squat", 50, 11, "good"))),
        )
        HomeScreen(
            prefs.copy(activePlanId = p.id, planSessionsDone = 4), catalog, {}, {}, {}, sessionsThisWeek = 2, onRetry = {},
            trainedDaysThisWeek = setOf(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY),
            activePlan = p,
            planSession = eu.motionforge.app.feature.plan.PlanSessions.build(p, 4, (catalog as eu.motionforge.app.feature.catalog.CatalogUiState.Ready).exercises, history),
        )
    }

    @Test fun train() = shot("02_train") {
        TrainScreen(catalog, Coach.DEFAULT, CatalogFilter(), {}, {}, {}, {}, {}, {})
    }

    @Test fun lesson() = shot("03_lesson") {
        LessonDetailScreen("bodyweight_squat", catalog, {}, {}, {}, {})
    }

    @Test fun progressEmpty() = shot("04_progress_empty") { ProgressScreen(emptyList(), Coach.DEFAULT) {} }

    @Test fun progress() = shot("05_progress") {
        val day = 24L * 3600 * 1000
        val now = System.currentTimeMillis()
        ProgressScreen(
            List(4) { i ->
                SessionRecord(
                    i.toLong(), "Short fitness session", if (i % 2 == 0) TrainingCategory.FITNESS else TrainingCategory.FIGHTING_FUNDAMENTALS,
                    now - i * 2 * day, 420 + 60 * i, 6, true,
                    listOf(
                        ExerciseRecord("bodyweight_squat", "Bodyweight Squat", 60, 12 - i, "good"),
                        ExerciseRecord("knee_push_up", "Knee Push-up", 45, 9 - (i % 2), "good"),
                    ),
                )
            },
            Coach.DEFAULT,
        ) {}
    }

    @Test fun onboardingWelcome() = shot("06_onboarding_welcome") { OnboardingContent(OnboardingState(), false) {} }

    @Test fun onboardingFocus() = shot("07_onboarding_focus") {
        OnboardingContent(OnboardingState(step = OnboardingStep.FOCUS, focus = TrainingCategory.FITNESS), false) {}
    }

    @Test fun profile() = shot("08_profile") { ProfileScreen(prefs, onOpenTechnicalChecks = {}, onResetData = {}) }

    @Composable
    private fun workout(started: Boolean) {
        val ctx = androidx.compose.ui.platform.LocalContext.current.applicationContext
        val vm = androidx.compose.runtime.remember {
            val plan = eu.motionforge.app.feature.session.SessionPlanner.quick(catalog.exercises, TrainingCategory.FITNESS)!!
            eu.motionforge.app.feature.session.SessionViewModel(
                plan, eu.motionforge.app.data.SessionRepository(ctx), eu.motionforge.app.data.ActiveSessionStore(ctx), "quick",
            ).also { if (started) it.onEvent(eu.motionforge.app.feature.session.SessionEvent.Start(false)) }
        }
        eu.motionforge.app.feature.session.SessionScreen(vm, catalog.exercises.associateBy { it.id }, Coach.DEFAULT, true, {}, {}, {})
    }

    @Test @Config(qualifiers = "w411dp-h891dp-xhdpi")
    fun workoutPortrait() = shot("09_workout") { workout(started = true) }

    @Test @Config(qualifiers = "w891dp-h411dp-land-xhdpi")
    fun workoutLandscape() = shot("10_workout_landscape") { workout(started = true) }

    @Test fun phoneSetup() = shot("11_phone_setup") { workout(started = false) }
}
