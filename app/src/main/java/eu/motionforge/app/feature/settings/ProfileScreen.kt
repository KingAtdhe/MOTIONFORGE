package eu.motionforge.app.feature.settings

import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.background
import androidx.compose.ui.semantics.heading
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.clickable
import android.Manifest
import android.content.pm.PackageManager
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import eu.motionforge.app.BuildConfig
import eu.motionforge.app.MotionForgeApplication
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.ui.Alignment
import androidx.compose.ui.semantics.Role
import androidx.compose.material3.Switch
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import eu.motionforge.app.core.design.CoachArt
import eu.motionforge.app.core.model.Coach
import eu.motionforge.app.core.design.Eyebrow
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.ScreenColumn
import eu.motionforge.app.data.UserPreferences
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(
    preferences: UserPreferences,
    onOpenTechnicalChecks: () -> Unit,
    onResetData: () -> Unit,
) {
    ScreenColumn(title = "Profile") { ProfileContent(preferences, onOpenTechnicalChecks, onResetData) }
}

/** Settings as part of a page: training, coach, voice, camera and privacy, safety, developer checks, reset. */
@Composable
fun androidx.compose.foundation.layout.ColumnScope.ProfileContent(
    preferences: UserPreferences,
    onOpenTechnicalChecks: () -> Unit,
    onResetData: () -> Unit,
) {
    val context = LocalContext.current
    fun granted() = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
    var cameraGranted by rememberSaveable { mutableStateOf(granted()) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { cameraGranted = granted() }
    var confirmReset by rememberSaveable { mutableStateOf(false) }
    val prefsRepo = remember { (context.applicationContext as MotionForgeApplication).container.preferences }
    val scope = rememberCoroutineScope()
    run {
        ProfileSection("Training") {
            Text("Focus: ${preferences.focus?.displayName ?: "not set"}", style = MaterialTheme.typography.bodyMedium)
            Text("Goal: ${preferences.goal?.displayName ?: "not set"}", style = MaterialTheme.typography.bodyMedium)
            Text("Account: guest (no account needed)", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        ProfileSection("Your coach") {
            Text("Who demonstrates the moves in lessons and sessions.", style = MaterialTheme.typography.bodyMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Coach.entries.forEach { c ->
                    val selected = preferences.coach == c
                    Surface(
                        modifier = Modifier
                            .weight(1f)
                            .selectable(selected = selected, onClick = { scope.launch { prefsRepo.setCoach(c) } }, role = Role.RadioButton),
                        shape = RoundedCornerShape(6.dp),
                        color = androidx.compose.ui.graphics.Color.Transparent,
                        border = if (selected) BorderStroke(2.dp, MaterialTheme.colorScheme.primary) else null,
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            eu.motionforge.app.core.design.MotionStudy(c.studyArt("boxing_cross"), Modifier.fillMaxWidth().height(180.dp), crop = true)
                            Text(
                                c.displayName + if (selected) ", selected" else "",
                                style = MaterialTheme.typography.labelLarge,
                                modifier = Modifier.padding(10.dp),
                            )
                        }
                    }
                }
            }
        }
        ProfileSection("Voice coach") {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column(Modifier.weight(1f)) {
                    Text("Spoken cues during sessions", style = MaterialTheme.typography.titleSmall)
                    Text(
                        "The coach announces each exercise, counts your reps, tells you when a hold timer pauses and says form adjustments out loud. " +
                            "Uses your phone's own text-to-speech voice.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Switch(
                    checked = preferences.voiceCues,
                    onCheckedChange = { on -> scope.launch { prefsRepo.setVoiceCues(on) } },
                    modifier = Modifier.semantics { contentDescription = "Spoken cues during sessions" },
                )
            }
        }
        ProfileSection("Reminders") { ReminderSettings(preferences) }
        ProfileSection("Camera & privacy") {
            Text(
                "Camera images are processed on this phone to estimate body landmarks. Frames are kept in " +
                    "memory only — never saved, recorded or uploaded. The camera is only used while a camera " +
                    "screen is open.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Camera permission: " + if (cameraGranted) "granted" else "not granted",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Stored on this phone: your focus, goal, chosen coach, voice and reminder settings and last viewed lesson. Nothing is sent to a server.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        ProfileSection("Safety") {
            Text(
                "MOTIONFORGE is an educational practice companion for adults. It is not a medical device, does not " +
                    "diagnose or prevent injury, and does not replace a qualified trainer or instructor. Fighting " +
                    "fundamentals are non-contact only. Stop if you feel pain, dizziness or unusual discomfort.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        ProfileSection("Developer", onClick = onOpenTechnicalChecks) {
            Text("Technical checks", style = MaterialTheme.typography.titleMedium)
            Text("Camera + pose tracking test and 3D animation test.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        eu.motionforge.app.core.design.SecondaryButton("Reset app data", onClick = { confirmReset = true }, color = MfColors.Halt)
        Text(
            "Version ${BuildConfig.VERSION_NAME}. Intended for adults (18+).",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }

    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text("Reset app data?") },
            text = { Text("This deletes your focus, goal and lesson history from this phone and returns you to the welcome screens. It cannot be undone.") },
            confirmButton = {
                TextButton(onClick = {
                    confirmReset = false
                    onResetData()
                }) { Text("Reset", color = MfColors.Halt) }
            },
            dismissButton = { TextButton(onClick = { confirmReset = false }) { Text("Cancel") } },
        )
    }
}

/** A settings group: a hairline above, a plain title, then its content. No card shell. */
@Composable
private fun ProfileSection(title: String, onClick: (() -> Unit)? = null, content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        eu.motionforge.app.core.design.SectionHeader(title)
        Spacer(Modifier.height(4.dp))
        content()
    }
}

/**
 * The optional training reminder: off by default. Turning it on explains why before Android asks for the
 * notification permission (Android 13+); without it the switch stays usable and says reminders can't appear.
 */
@Composable
private fun ReminderSettings(preferences: UserPreferences) {
    val context = LocalContext.current
    val prefsRepo = remember { (context.applicationContext as MotionForgeApplication).container.preferences }
    val scope = rememberCoroutineScope()
    var allowed by remember { mutableStateOf(eu.motionforge.app.feature.reminders.Reminders.notificationsAllowed(context)) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { allowed = eu.motionforge.app.feature.reminders.Reminders.notificationsAllowed(context) }
    val schedule = preferences.reminder

    fun save(on: Boolean, s: eu.motionforge.app.feature.reminders.ReminderSchedule) {
        scope.launch {
            prefsRepo.setReminder(on, s)
            eu.motionforge.app.feature.reminders.Reminders.apply(context, preferences.copy(reminderOn = on, reminder = s))
        }
    }
    val askNotify = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestPermission(),
    ) { allowed = eu.motionforge.app.feature.reminders.Reminders.notificationsAllowed(context) }

    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f)) {
            Text("Training reminder", style = MaterialTheme.typography.titleSmall)
            Text(
                "One notification on the days you pick, at the time you pick. It stays quiet on a day you've already trained. " +
                    "Android asks for permission to show notifications the first time.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Switch(
            checked = preferences.reminderOn,
            onCheckedChange = { on ->
                save(on, schedule)
                if (on && android.os.Build.VERSION.SDK_INT >= 33 &&
                    ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
                ) askNotify.launch(Manifest.permission.POST_NOTIFICATIONS)
            },
            modifier = Modifier.semantics { contentDescription = "Training reminder" },
        )
    }
    if (!preferences.reminderOn) return

    // days: at least one stays chosen
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        java.time.DayOfWeek.entries.forEach { d ->
            val on = d in schedule.days
            val label = eu.motionforge.app.feature.reminders.ReminderSchedule.SHORT[d.ordinal]
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .heightIn(min = 48.dp)
                    .selectable(
                        selected = on,
                        role = Role.Checkbox,
                        onClick = {
                            val days = if (on) schedule.days - d else schedule.days + d
                            if (days.isNotEmpty()) save(true, schedule.copy(days = days))
                        },
                    )
                    .semantics { contentDescription = label + if (on) ", on" else ", off" },
                shape = RoundedCornerShape(6.dp),
                color = if (on) MaterialTheme.colorScheme.primary else androidx.compose.ui.graphics.Color.Transparent,
                border = BorderStroke(1.dp, if (on) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline),
            ) {
                androidx.compose.foundation.layout.Box(contentAlignment = Alignment.Center) {
                    Text(
                        label.take(2),
                        style = MaterialTheme.typography.labelLarge,
                        color = if (on) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
                    )
                }
            }
        }
    }
    OutlinedButton(
        onClick = {
            android.app.TimePickerDialog(
                context,
                { _, h, m -> save(true, schedule.copy(minuteOfDay = h * 60 + m)) },
                schedule.minuteOfDay / 60, schedule.minuteOfDay % 60,
                android.text.format.DateFormat.is24HourFormat(context),
            ).show()
        },
        modifier = Modifier.heightIn(min = 48.dp),
    ) { Text("Time: %02d:%02d".format(schedule.minuteOfDay / 60, schedule.minuteOfDay % 60)) }
    Text(schedule.describe(), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    if (!allowed) {
        Text(
            "Notifications are off for MOTIONFORGE, so the reminder can't appear. You can allow them in Android's settings.",
            style = MaterialTheme.typography.bodyMedium,
            color = MfColors.Halt,
        )
        TextButton(onClick = {
            context.startActivity(
                android.content.Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                    .putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, context.packageName)
                    .addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK),
            )
        }) { Text("Open notification settings") }
    }
}
