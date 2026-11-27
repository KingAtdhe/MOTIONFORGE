package eu.motionforge.app.feature.reminders

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import eu.motionforge.app.MainActivity
import eu.motionforge.app.MotionForgeApplication
import eu.motionforge.app.R
import eu.motionforge.app.data.UserPreferences
import eu.motionforge.app.feature.plan.TrainingPlans
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.time.ZonedDateTime

/**
 * The optional training reminder. One inexact alarm at a time (no exact-alarm permission needed; Android may move it
 * by a few minutes to save battery), re-armed after each firing, after a reboot and when the clock or time zone
 * changes. Nothing is shown without the notification permission, and nothing leaves the phone.
 */
object Reminders {
    private const val CHANNEL = "reminders"
    private const val NOTIFICATION_ID = 4301
    private const val REQUEST = 4302
    const val ACTION_FIRE = "eu.motionforge.app.REMINDER"

    fun notificationsAllowed(context: Context): Boolean =
        (Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) &&
            NotificationManagerCompat.from(context).areNotificationsEnabled()

    private fun pending(context: Context, create: Boolean): PendingIntent? = PendingIntent.getBroadcast(
        context, REQUEST,
        Intent(context, ReminderReceiver::class.java).setAction(ACTION_FIRE),
        PendingIntent.FLAG_IMMUTABLE or if (create) PendingIntent.FLAG_UPDATE_CURRENT else PendingIntent.FLAG_NO_CREATE,
    )

    /** Arm (or cancel) the next reminder for [prefs]. Returns the time armed, or null when none is. */
    fun apply(context: Context, prefs: UserPreferences, now: ZonedDateTime = ZonedDateTime.now(ReminderSchedule.zone())): ZonedDateTime? {
        val am = context.getSystemService(AlarmManager::class.java)
        val next = if (prefs.reminderOn && prefs.onboardingComplete) prefs.reminder.nextAfter(now) else null
        if (next == null) {
            am.cancel(pending(context, create = true)!!)
            return null
        }
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, next.toInstant().toEpochMilli(), pending(context, create = true)!!)
        return next
    }

    fun cancel(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java)
        // the same PendingIntent identity cancels the alarm (it is not cancelled itself, so a later arm can't miss it)
        am.cancel(pending(context, create = true)!!)
        NotificationManagerCompat.from(context).cancel(NOTIFICATION_ID)
    }

    /** Show today's reminder unless a session was already saved today. */
    internal fun show(context: Context, prefs: UserPreferences, sessionStarts: List<Long>, now: ZonedDateTime) {
        if (!prefs.reminderOn || !notificationsAllowed(context)) return
        if (ReminderSchedule.trainedToday(sessionStarts, now)) return
        val plan = TrainingPlans.byId(prefs.activePlanId)
        val text = eu.motionforge.app.core.i18n.I18n.t(ReminderSchedule.message(plan?.name, plan?.let { prefs.planSessionsDone }, plan?.totalSessions))
        ensureChannel(context)
        val open = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val n = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_workout)
            .setContentTitle(eu.motionforge.app.core.i18n.I18n.t("Time to train?"))
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(open)
            .setAutoCancel(true)
            // a reminder from the morning is no use at midnight
            .setTimeoutAfter(6 * 60 * 60 * 1000L)
            .build()
        try {
            NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, n)
        } catch (_: SecurityException) {
            // permission withdrawn: stay quiet
        }
    }

    private fun ensureChannel(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL, "Training reminders", NotificationManager.IMPORTANCE_DEFAULT).apply {
                    description = "One reminder on the training days you chose in Profile."
                },
            )
        }
    }
}

/** Fires the reminder and re-arms the next one; also re-arms after a reboot, an app update or a clock change. */
class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val app = context.applicationContext as? MotionForgeApplication ?: return
        val done = goAsync()
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            try {
                val prefs = app.container.preferences.preferences.first()
                // a reminder can start the app's process on its own: load the chosen language for its text
                eu.motionforge.app.core.i18n.I18nLoader.apply(context, eu.motionforge.app.core.i18n.I18n.resolve(prefs.language))
                val now = ZonedDateTime.now(ReminderSchedule.zone())
                if (intent.action == Reminders.ACTION_FIRE) {
                    val starts = app.container.sessions.history.first().map { it.startedAtMillis }
                    Reminders.show(context, prefs, starts, now)
                }
                Reminders.apply(context, prefs, now)
            } finally {
                done.finish()
            }
        }
    }
}
