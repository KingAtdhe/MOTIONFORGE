package eu.motionforge.app.screenshots

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
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
import eu.motionforge.app.core.model.Coach
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.time.DayOfWeek

/**
 * Renders the main screens with sample data to PNGs in build/reports/screenshots/ (uploaded by CI with the test
 * reports), so the design can be reviewed without a device. Not a pixel-comparison test: it fails only if a screen
 * cannot be composed.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w411dp-h1900dp-xhdpi")
class ScreenshotTest {
    @get:Rule val compose = createComposeRule()

    private val catalog = CatalogUiState.Ready(
        ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText()),
    )
    private val prefs = UserPreferences(
        onboardingComplete = true, focus = TrainingCategory.FITNESS, goal = TrainingGoal.BUILD_ROUTINE,
        lastViewedExerciseId = "bodyweight_squat",
    )

    private fun shot(name: String, content: @Composable () -> Unit) {
        compose.setContent {
            MotionForgeTheme {
                Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) { content() }
            }
        }
        compose.waitForIdle()
        val bmp = compose.onRoot().captureToImage().asAndroidBitmap()
        val out = File("build/reports/screenshots").apply { mkdirs() }
        File(out, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test fun home() = shot("01_home") {
        HomeScreen(prefs, catalog, {}, {}, {}, sessionsThisWeek = 2, onRetry = {}, trainedDaysThisWeek = setOf(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY))
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
                    listOf(ExerciseRecord("bodyweight_squat", "Bodyweight Squat", 60, 12, "good")),
                )
            },
            Coach.DEFAULT,
        ) {}
    }

    @Test fun onboardingWelcome() = shot("06_onboarding_welcome") { OnboardingContent(OnboardingState(), false) {} }

    @Test fun onboardingFocus() = shot("07_onboarding_focus") {
        OnboardingContent(OnboardingState(step = OnboardingStep.FOCUS, focus = TrainingCategory.FITNESS), false) {}
    }
}
