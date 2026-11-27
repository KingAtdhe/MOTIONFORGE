package eu.motionforge.app.feature.reminders

import android.app.AlarmManager
import android.app.NotificationManager
import androidx.test.core.app.ApplicationProvider
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.data.UserPreferences
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import java.time.ZoneId
import java.time.ZonedDateTime

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class RemindersAlarmTest {
    private val app get() = ApplicationProvider.getApplicationContext<MotionForgeApplication>()
    private val alarms get() = shadowOf(app.getSystemService(AlarmManager::class.java))
    private val notes get() = shadowOf(app.getSystemService(NotificationManager::class.java))
    private val now = ZonedDateTime.of(2026, 11, 25, 9, 0, 0, 0, ZoneId.systemDefault())
    private val prefs = UserPreferences(onboardingComplete = true, focus = null, goal = null, lastViewedExerciseId = null, reminderOn = true)

    @Test
    fun armsTheNextReminderAndCancelsWhenTurnedOff() {
        val next = Reminders.apply(app, prefs, now)
        assertEquals(ReminderSchedule.DEFAULT.nextAfter(now), next)
        assertEquals(next!!.toInstant().toEpochMilli(), alarms.nextScheduledAlarm!!.triggerAtTime)
        assertNull(Reminders.apply(app, prefs.copy(reminderOn = false), now))
        assertNull(alarms.nextScheduledAlarm)
    }

    @Test
    fun resetCancelsTheReminder() {
        Reminders.apply(app, prefs, now)
        Reminders.cancel(app)
        assertNull(alarms.nextScheduledAlarm)
    }

    @Test
    fun showsOnceButStaysQuietAfterTraining() {
        shadowOf(app).grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS)
        Reminders.show(app, prefs, listOf(now.minusHours(2).toInstant().toEpochMilli()), now)
        assertEquals(0, notes.allNotifications.size)
        Reminders.show(app, prefs, emptyList(), now)
        assertEquals(1, notes.allNotifications.size)
        assertNotNull(notes.getNotificationChannel("reminders"))
    }
}
