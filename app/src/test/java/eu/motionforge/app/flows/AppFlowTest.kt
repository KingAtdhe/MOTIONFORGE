package eu.motionforge.app.flows

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeUp
import androidx.compose.ui.test.printToString
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import androidx.test.core.app.ApplicationProvider
import eu.motionforge.app.MainActivity
import eu.motionforge.app.MotionForgeApp
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.core.design.MotionForgeTheme
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal
import eu.motionforge.app.data.ExerciseCatalogParser
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.plan.TrainingPlans
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.shadows.ShadowLooper
import java.io.File
import java.time.Duration

/**
 * End-to-end flows through the real app (Robolectric): onboarding, sessions from Home, every lesson page and every
 * lesson as a practice session, training plans, and picking up a session Android closed. The 3D view falls back to
 * the motion study here (no GPU), as it does on phones without 3D; the camera is not used.
 *
 * The frame clock and the main looper are driven by hand ([pump]) because the workout screen has looping animations
 * that would never let an automatic clock settle.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w411dp-h891dp-xhdpi")
class AppFlowTest {
    @get:Rule val timeout: org.junit.rules.Timeout = org.junit.rules.Timeout.seconds(240)
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    private val app get() = ApplicationProvider.getApplicationContext<MotionForgeApplication>()

    @org.junit.Before
    fun freshInstall() {
        // the workout-notification permission dialog has no answer under Robolectric: granted up front
        org.robolectric.Shadows.shadowOf(app).grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS)
        // DataStore and the database are process-wide: every test starts from a fresh install
        runBlocking {
            app.container.preferences.clearAll()
            app.container.sessions.deleteAll()
        }
        app.container.activeSession.clear()
        pump(300, 100)
    }

    // ------------------------------------------------------------------------------------------------ helpers
    private fun pump(ms: Long = 200, sleep: Long = 30) {
        compose.mainClock.autoAdvance = false
        var left = ms
        while (left > 0) {
            val step = minOf(left, 100L)
            compose.mainClock.advanceTimeBy(step)
            ShadowLooper.idleMainLooper(step, java.util.concurrent.TimeUnit.MILLISECONDS)
            left -= step
        }
        if (sleep > 0) Thread.sleep(sleep)                         // repositories work on Dispatchers.IO
        ShadowLooper.idleMainLooper()
    }

    private fun exists(text: String, substring: Boolean = false) =
        compose.onAllNodesWithText(text, substring = substring, useUnmergedTree = true).fetchSemanticsNodes().isNotEmpty()

    private fun existsDesc(desc: String) =
        compose.onAllNodesWithContentDescription(desc, useUnmergedTree = true).fetchSemanticsNodes().isNotEmpty()

    private fun waitFor(what: String, timeoutMs: Long = 8000, check: () -> Boolean) {
        var t = 0L
        while (!check()) {
            if (t > timeoutMs) fail("Timed out waiting for: $what")
            pump(200, 40)
            t += 200
        }
    }

    private fun waitForText(text: String, substring: Boolean = false) = waitFor("'$text'") { exists(text, substring) }

    private fun click(text: String, substring: Boolean = false) {
        waitForText(text, substring)
        val node = compose.onAllNodesWithText(text, substring = substring)[0]
        if (runCatching { node.performScrollTo() }.isFailure) {
            // bring it into view by swiping the screen up (bounded: never loops forever)
            repeat(6) {
                val shown = runCatching { node.assertIsDisplayed() }.isSuccess
                if (!shown) {
                    compose.onAllNodes(androidx.compose.ui.test.isRoot())[0].performTouchInput { swipeUp() }
                    pump(300)
                }
            }
        }
        pump(100)
        node.performClick()
        pump()
    }

    private fun clickDesc(desc: String) {
        waitFor("button '$desc'") { existsDesc(desc) }
        compose.onAllNodesWithContentDescription(desc)[0].performClick()
        pump()
    }

    private fun onboard(gender: String = "Woman", focus: String = "Fitness") {
        click("Get started")
        click("I am 18 or older")
        click("I have read and understand this")
        click("Continue")
        click(focus)
        click("Continue")
        click(TrainingGoal.BUILD_ROUTINE.displayName)
        click("Continue")
        click(gender)
        click("Start training")
    }

    /** Seconds of workout time: the session ticker runs on the main looper. */
    private fun train(seconds: Int) = repeat(seconds) { pump(1000, 0) }

    private fun endAndSave() {
        click("Tap anywhere to pause", substring = true)
        clickDesc("End")
        waitForText("Session ended")
        click("Save session")
        waitForText("Saved to your progress on this phone.")
    }

    private fun sessionCount(): Int = runBlocking { app.container.sessions.history.first().size }

    // ------------------------------------------------------------------------------------------------ flows
    @Test
    fun onboarding_then_quick_session_is_saved_and_counted() {
        onboard()
        waitForText("Start session")
        val prefs = runBlocking { app.container.preferences.preferences.first() }
        assertTrue(prefs.onboardingComplete)
        assertEquals(TrainingCategory.FITNESS, prefs.focus)
        assertEquals(Coach.FEMALE, prefs.coach)

        click("Start session")
        click("Start without camera")
        train(20)
        assertTrue("timer should be running", exists("Tap anywhere to pause", substring = true))
        endAndSave()
        assertEquals(1, sessionCount())
        click("Done")
        waitForText("Start session")                              // back on Home
        assertEquals("the saved session must not be offered again", false, exists("Resume"))
    }

    @Test
    fun male_coach_and_fighting_focus_from_onboarding() {
        onboard(gender = "Man", focus = "Fighting Fundamentals")
        waitForText("Start session")
        val prefs = runBlocking { app.container.preferences.preferences.first() }
        assertEquals(Coach.MALE, prefs.coach)
        assertEquals(TrainingCategory.FIGHTING_FUNDAMENTALS, prefs.focus)
        click("Start session")
        waitForText("Start without camera")
        assertTrue("a fighting session starts with boxing moves", exists("Boxing", substring = true))
    }

    @Test
    fun back_during_a_workout_does_not_throw_the_workout_away() {
        onboard()
        click("Start session")
        click("Start without camera")
        train(12)
        compose.activityRule.scenario.onActivity { it.onBackPressedDispatcher.onBackPressed() }
        pump()
        // the workout is paused (resume possible) or ended with the save screen — never silently lost
        val paused = existsDesc("Resume")
        val summary = exists("Save session")
        assertTrue("after Back the workout must be paused or offer saving", paused || summary)
        if (paused) {
            clickDesc("Resume")
            train(3)
            assertTrue(exists("Tap anywhere to pause", substring = true))
        }
    }

    @Test
    fun skipping_through_every_step_finishes_the_session() {
        onboard()
        click("Start session")
        click("Start without camera")
        var guard = 0
        while (!exists("Session complete") && !exists("Session ended") && guard++ < 30) {
            train(4)
            click("Tap anywhere to pause", substring = true)
            val skip = if (existsDesc("Skip rest")) "Skip rest" else "Skip"
            clickDesc(skip)
        }
        waitFor("summary") { exists("Session complete") || exists("Session ended") }
        click("Save session")
        var waited = 0
        while (!exists("Saved to your progress on this phone.")) {
            val failed = exists("Saving failed. Please try again.")
            val tooShort = exists("This session was too short to save.")
            if (waited > 15000) fail(
                "not saved; failed=" + failed + ", tooShort=" + tooShort + ", saving=" + exists("Saving…") +
                    ", saveButton=" + exists("Save session") + "\n" +
                    compose.onAllNodes(androidx.compose.ui.test.isRoot())[0].printToString().take(4000),
            )
            pump(200, 40); waited += 200
        }
        assertEquals(1, sessionCount())
    }

    @Test
    fun training_plan_starts_and_its_session_runs() {
        onboard()
        runBlocking { app.container.preferences.startPlan(TrainingPlans.FOUNDATIONS.id) }
        waitForText("Start plan session")
        click("Start plan session")
        click("Start without camera")
        train(12)
        endAndSave()
        click("Done")
        pump(400, 200)
        val prefs = runBlocking { app.container.preferences.preferences.first() }
        assertEquals("a saved plan session moves the plan on", 1, prefs.planSessionsDone)
    }

    @Test
    fun saved_history_survives_a_restart() {
        onboard()
        click("Start session")
        click("Start without camera")
        train(15)
        endAndSave()
        click("Done")
        compose.activityRule.scenario.recreate()
        pump(400, 200)
        assertEquals(1, sessionCount())
    }
}

/**
 * Every lesson page opens, and every lesson runs as a practice session, for both coaches. Drives the real
 * [MotionForgeApp] with its own navigation controller (the lesson list is long; going through the scrolling list for
 * 58 lessons would test the list, not the lessons).
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w411dp-h891dp-xhdpi")
class EveryLessonTest {
    @get:Rule val timeout: org.junit.rules.Timeout = org.junit.rules.Timeout.seconds(1200)
    @get:Rule val compose = createAndroidComposeRule<androidx.activity.ComponentActivity>()

    private val app get() = ApplicationProvider.getApplicationContext<MotionForgeApplication>()
    private val lessons = ExerciseCatalogParser.parse(File("src/main/assets/${ExerciseCatalogParser.ASSET_PATH}").readText())

    @org.junit.Before
    fun freshInstall() {
        // the workout-notification permission dialog has no answer under Robolectric: granted up front
        org.robolectric.Shadows.shadowOf(app).grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS)
        // DataStore and the database are process-wide: every test starts from a fresh install
        runBlocking {
            app.container.preferences.clearAll()
            app.container.sessions.deleteAll()
        }
        app.container.activeSession.clear()
        pump(300, 100)
    }

    private fun pump(ms: Long = 200, sleep: Long = 30) {
        compose.mainClock.autoAdvance = false
        var left = ms
        while (left > 0) {
            val step = minOf(left, 100L)
            compose.mainClock.advanceTimeBy(step)
            ShadowLooper.idleMainLooper(step, java.util.concurrent.TimeUnit.MILLISECONDS)
            left -= step
        }
        if (sleep > 0) Thread.sleep(sleep)
        ShadowLooper.idleMainLooper()
    }

    private fun exists(text: String, substring: Boolean = false) =
        compose.onAllNodesWithText(text, substring = substring, useUnmergedTree = true).fetchSemanticsNodes().isNotEmpty()

    private fun waitFor(what: String, timeoutMs: Long = 8000, check: () -> Boolean) {
        var t = 0L
        while (!check()) {
            if (t > timeoutMs) fail("Timed out waiting for: $what")
            pump(200, 40)
            t += 200
        }
    }

    private fun run(coach: Coach) {
        val prefs = UserPreferences(
            onboardingComplete = true, focus = TrainingCategory.FITNESS, goal = TrainingGoal.BUILD_ROUTINE,
            lastViewedExerciseId = null, coach = coach, voiceCues = false,
        )
        lateinit var nav: NavHostController
        compose.mainClock.autoAdvance = false
        compose.setContent {
            nav = rememberNavController()
            MotionForgeTheme { MotionForgeApp(prefs, 0, app.container, onResetData = {}, navController = nav) }
        }
        waitFor("Home") { exists("Start session") }
        val problems = mutableListOf<String>()
        for (lesson in lessons) {
            try {
                compose.runOnUiThread { nav.navigate("lesson/${lesson.id}") }
                waitFor("lesson ${lesson.id}") { exists(lesson.name) && exists("Start practice") }
                compose.runOnUiThread { app.container.activeSession.clear(); nav.navigate("session/lesson-${lesson.id}") }
                waitFor("setup ${lesson.id}") { exists("Start without camera") }
                compose.onAllNodesWithText("Start without camera")[0].let { runCatching { it.performScrollTo() }; it.performClick() }
                pump()
                repeat(3) { pump(1000, 0) }
                waitFor("running ${lesson.id}") { exists(lesson.name) }
                compose.runOnUiThread { nav.popBackStack("home", inclusive = false) }
                pump(300)
            } catch (t: Throwable) {
                problems += "${lesson.id}: ${t.message?.lineSequence()?.firstOrNull()}"
                runCatching { compose.runOnUiThread { nav.popBackStack("home", inclusive = false) } }
                pump(300)
            }
        }
        assertTrue("Lessons with problems (${coach.name}):\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // ~8 minutes each: its own CI step (MF_FULL_FLOWS=1)
    @Test fun every_lesson_opens_and_runs_female() { org.junit.Assume.assumeTrue(System.getenv("MF_FULL_FLOWS") == "1"); run(Coach.FEMALE) }

    /** Android closes the app mid-workout: Home offers the unfinished session and it comes back paused, same step. */
    @Test
    fun unfinished_session_is_offered_on_home_and_resumes_paused() {
        val prefs = UserPreferences(
            onboardingComplete = true, focus = TrainingCategory.FITNESS, goal = TrainingGoal.BUILD_ROUTINE,
            lastViewedExerciseId = null, voiceCues = false,
        )
        var generation by androidx.compose.runtime.mutableIntStateOf(0)
        lateinit var nav: NavHostController
        compose.mainClock.autoAdvance = false
        compose.setContent {
            androidx.compose.runtime.key(generation) {
                nav = rememberNavController()
                MotionForgeTheme { MotionForgeApp(prefs, generation, app.container, onResetData = {}, navController = nav) }
            }
        }
        waitFor("Home") { exists("Start session") }
        compose.onAllNodesWithText("Start session")[0].let { runCatching { it.performScrollTo() }; it.performClick() }
        pump()
        waitFor("setup") { exists("Start without camera") }
        compose.onAllNodesWithText("Start without camera")[0].let { runCatching { it.performScrollTo() }; it.performClick() }
        pump()
        repeat(20) { pump(1000, 0) }
        // pause, so the clock stands still while the state on disk is compared
        compose.onAllNodesWithText("Tap anywhere to pause", substring = true)[0].performClick()
        pump(500, 300)
        val before = app.container.activeSession.read()
        assertTrue("a running session is kept on disk", before != null)
        // a fresh start of the app (new navigation, new view models): it opens on Home
        compose.runOnUiThread { generation++ }
        pump(400, 200)
        waitFor("Resume on Home") { exists("Resume") }
        compose.onAllNodesWithText("Resume")[0].let { runCatching { it.performScrollTo() }; it.performClick() }
        pump(400, 200)
        waitFor("restored workout, paused") {
            compose.onAllNodesWithContentDescription("Resume", useUnmergedTree = true).fetchSemanticsNodes().isNotEmpty()
        }
        val after = app.container.activeSession.read()
        assertEquals(before!!.state.stepIndex, after!!.state.stepIndex)
        assertEquals(before.state.elapsedTotal, after.state.elapsedTotal)
    }

    // ~8 minutes each: its own CI step (MF_FULL_FLOWS=1)
    @Test fun every_lesson_opens_and_runs_male() { org.junit.Assume.assumeTrue(System.getenv("MF_FULL_FLOWS") == "1"); run(Coach.MALE) }
}
