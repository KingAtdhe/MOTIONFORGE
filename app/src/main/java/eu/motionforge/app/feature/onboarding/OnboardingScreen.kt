package eu.motionforge.app.feature.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.ui.draw.alpha
import eu.motionforge.app.core.design.CoachArt
import eu.motionforge.app.core.model.Coach
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.SelectableOption
import eu.motionforge.app.core.model.TrainingCategory
import eu.motionforge.app.core.model.TrainingGoal

@Composable
fun OnboardingScreen(viewModel: OnboardingViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val saving by viewModel.saving.collectAsStateWithLifecycle()
    OnboardingContent(state = state, saving = saving, onEvent = viewModel::onEvent)
}

@Composable
internal fun OnboardingContent(state: OnboardingState, saving: Boolean, onEvent: (OnboardingEvent) -> Unit) {
    // System back walks the flow instead of leaving the app mid-onboarding.
    BackHandler(enabled = state.step != OnboardingStep.WELCOME) { onEvent(OnboardingEvent.Back) }

    Column(
        Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .padding(horizontal = 20.dp, vertical = 16.dp),
    ) {
        Text(
            "Step ${state.progressIndex} of ${OnboardingState.VISIBLE_STEPS}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.padding(top = 6.dp))
        LinearProgressIndicator(
            progress = { state.progressIndex / OnboardingState.VISIBLE_STEPS.toFloat() },
            modifier = Modifier.fillMaxWidth().height(3.dp),
            color = MaterialTheme.colorScheme.onBackground,
            trackColor = MaterialTheme.colorScheme.outline,
            gapSize = 0.dp,
            drawStopIndicator = {},
        )

        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(top = 28.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            when (state.step) {
                OnboardingStep.WELCOME -> WelcomeStep()
                OnboardingStep.AGE -> AgeStep(onEvent)
                OnboardingStep.UNDER_AGE -> UnderAgeStep()
                OnboardingStep.SAFETY -> SafetyStep(state.safetyAcknowledged, onEvent)
                OnboardingStep.FOCUS -> FocusStep(state.focus, onEvent)
                OnboardingStep.GOAL -> GoalStep(state.goal, onEvent)
                OnboardingStep.COACH -> CoachStep(state.gender, onEvent)
            }
        }

        Row(Modifier.fillMaxWidth().padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            if (state.step != OnboardingStep.WELCOME) {
                TextButton(onClick = { onEvent(OnboardingEvent.Back) }) { Text("Back") }
            }
            Spacer(Modifier.weight(1f))
            // The age step is answered with its own two buttons; under-age has no way forward.
            if (state.step != OnboardingStep.AGE && state.step != OnboardingStep.UNDER_AGE) {
                Button(
                    onClick = { onEvent(OnboardingEvent.Continue) },
                    enabled = state.canContinue && !saving,
                    modifier = Modifier.heightIn(min = 56.dp),
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(6.dp),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 28.dp),
                    colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = eu.motionforge.app.core.design.MfColors.Yellow, contentColor = androidx.compose.ui.graphics.Color.Black),
                ) {
                    Text(
                        when {
                            saving -> "Saving…"
                            state.isFinalStep -> "Start training"
                            state.step == OnboardingStep.WELCOME -> "Get started"
                            else -> "Continue"
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun ColumnScope.Heading(title: String, body: String) {
    Text(title, style = MaterialTheme.typography.headlineLarge)
    Text(body, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
private fun ColumnScope.WelcomeStep() {
    eu.motionforge.app.core.design.MotionStudy(
        Coach.FEMALE.studyArt("bodyweight_squat"),
        Modifier.fillMaxWidth().height(340.dp),
        description = "A squat shown as a motion study: several moments of the movement on one picture",
    )
    Heading(
        "See the movement. Practise it. Understand your progress.",
        "Short guided sessions for beginner fitness and non-contact boxing fundamentals. A 3D coach demonstrates " +
            "every lesson, and the camera can track your movement on this phone.",
    )
    Panel {
        Text("No account needed. Your progress stays on this phone.", style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ColumnScope.AgeStep(onEvent: (OnboardingEvent) -> Unit) {
    Heading("Are you 18 or older?", "This first version of MOTIONFORGE is designed for adults. Your answer is not stored.")
    Button(
        onClick = { onEvent(OnboardingEvent.AgeAnswered(isAdult = true)) },
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(6.dp),
    ) { Text("I am 18 or older") }
    OutlinedButton(
        onClick = { onEvent(OnboardingEvent.AgeAnswered(isAdult = false)) },
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(6.dp),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, MaterialTheme.colorScheme.onBackground),
    ) { Text("I am under 18") }
}

@Composable
private fun ColumnScope.UnderAgeStep() {
    Heading(
        "MOTIONFORGE is for adults for now",
        "This version isn't designed for people under 18, so we can't continue. If you want to get active, " +
            "a parent, PE teacher or local sports club can help you find something suitable.",
    )
}

@Composable
private fun ColumnScope.SafetyStep(acknowledged: Boolean, onEvent: (OnboardingEvent) -> Unit) {
    Heading("Before you start", "Please read this once. You can find it again in Profile.")
    Panel {
        Eyebrow("Safety", color = MfColors.Caution)
        SafetyLine("MOTIONFORGE is an educational practice companion. It is not a medical device and does not diagnose, treat or prevent any condition or injury.")
        SafetyLine("It does not replace a qualified personal trainer or martial arts instructor.")
        SafetyLine("Camera feedback, when available, is limited and may be wrong. It never certifies technique.")
        SafetyLine("All fighting fundamentals are non-contact. Never strike people or objects.")
        SafetyLine("Use clear, non-slip floor space. Stop if you feel pain, dizziness or unusual discomfort.")
        SafetyLine("If you are unsure whether an activity is suitable for you, ask a qualified professional first.")
    }
    Row(
        Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .toggleable(
                value = acknowledged,
                role = Role.Checkbox,
                onValueChange = { onEvent(OnboardingEvent.SafetyAcknowledged(it)) },
            ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(checked = acknowledged, onCheckedChange = null)
        Spacer(Modifier.width(8.dp))
        Text("I have read and understand this", style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun SafetyLine(text: String) {
    Text("•  $text", style = MaterialTheme.typography.bodyMedium)
}

@Composable
private fun ColumnScope.FocusStep(selected: TrainingCategory?, onEvent: (OnboardingEvent) -> Unit) {
    Heading("What would you like to start with?", "You can open every lesson either way. This only sets your suggestions.")
    SelectableOption(
        title = TrainingCategory.FITNESS.displayName,
        description = "Bodyweight basics: warm-up, squat, hip hinge, push-up.",
        selected = selected == TrainingCategory.FITNESS,
        onSelect = { onEvent(OnboardingEvent.FocusChosen(TrainingCategory.FITNESS)) },
    )
    SelectableOption(
        title = TrainingCategory.FIGHTING_FUNDAMENTALS.displayName,
        description = "Non-contact boxing basics: stance, jab, cross, guard and footwork.",
        selected = selected == TrainingCategory.FIGHTING_FUNDAMENTALS,
        onSelect = { onEvent(OnboardingEvent.FocusChosen(TrainingCategory.FIGHTING_FUNDAMENTALS)) },
    )
}

@Composable
private fun ColumnScope.GoalStep(selected: TrainingGoal?, onEvent: (OnboardingEvent) -> Unit) {
    Heading("Pick a beginner goal", "There's no pressure and no streaks. Change it any time by resetting in Profile.")
    TrainingGoal.entries.forEach { goal ->
        SelectableOption(
            title = goal.displayName,
            description = goal.description,
            selected = selected == goal,
            onSelect = { onEvent(OnboardingEvent.GoalChosen(goal)) },
        )
    }
}

@Composable
private fun ColumnScope.CoachStep(selected: GenderAnswer?, onEvent: (OnboardingEvent) -> Unit) {
    Heading(
        "Are you a woman or a man?",
        "We'll show you a matching 3D coach. Only the coach choice is saved on this phone — you can switch coach any time in Profile.",
    )
    CoachPair(Modifier.fillMaxWidth().height(220.dp), highlight = selected?.let { if (it == GenderAnswer.MAN) Coach.MALE else Coach.FEMALE })
    GenderAnswer.entries.forEach { g ->
        SelectableOption(
            title = g.label,
            description = when (g) {
                GenderAnswer.WOMAN -> "Train with the female coach."
                GenderAnswer.MAN -> "Train with the male coach."
                GenderAnswer.NOT_SAID -> "We'll start you with the female coach."
            },
            selected = selected == g,
            onSelect = { onEvent(OnboardingEvent.GenderChosen(g)) },
        )
    }
}

/** Both coaches side by side; the highlighted one is shown at full strength. Decorative (choices are labelled). */
@Composable
private fun CoachPair(modifier: Modifier, highlight: Coach? = null) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        listOf(Coach.FEMALE to "bodyweight_squat", Coach.MALE to "boxing_cross").forEach { (c, lesson) ->
            val dim = highlight != null && highlight != c
            eu.motionforge.app.core.design.MotionStudy(
                c.studyArt(lesson),
                Modifier.weight(1f).fillMaxHeight().alpha(if (dim) 0.35f else 1f),
                crop = true,
            )
        }
    }
}
