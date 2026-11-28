package eu.motionforge.app.feature.settings

import androidx.compose.runtime.Composable
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.feature.progress.SessionRecord
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.progress.ProgressContent

/** The "You" tab: your progress first, then settings, on one page (three tabs instead of four). */
@Composable
fun YouScreen(
    history: List<SessionRecord>?,
    preferences: UserPreferences,
    coach: Coach,
    onStartSession: () -> Unit,
    onOpenTechnicalChecks: () -> Unit,
    onResetData: () -> Unit,
) {
    ScreenColumn(title = "You") {
        ProgressContent(history, coach, onStartSession, preferences.weeklyGoal, preferences.milestones, preferences.challenges)
        ProfileContent(preferences, onOpenTechnicalChecks, onResetData)
    }
}
