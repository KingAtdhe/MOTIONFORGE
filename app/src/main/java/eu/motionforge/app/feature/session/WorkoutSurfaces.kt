package eu.motionforge.app.feature.session

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import eu.motionforge.app.MainActivity
import eu.motionforge.app.R
import eu.motionforge.app.core.design.formatClock

/**
 * The running workout outside the app: an ongoing notification (shown as a Live Update chip on Android 16 where the
 * system promotes it) with the current move and a countdown. Nothing is shown without the notification permission.
 */
class WorkoutNotifier(private val context: Context) {
    private val manager = NotificationManagerCompat.from(context)

    private fun allowed(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    fun update(state: SessionState) {
        if (!allowed()) return
        ensureChannel()
        val step = state.currentStep
        val paused = state.phase == SessionPhase.PAUSED
        val title = when (step) {
            is SessionStep.Work -> step.name
            is SessionStep.Rest -> "Rest, next: ${step.nextName}"
        }
        val text = buildString {
            if (step is SessionStep.Work) append("Exercise ${state.workIndex} of ${state.plan.workCount}")
            if (step is SessionStep.Work && step.countsReps && state.cameraUsed) append(", ${state.stepReps} reps")
            if (paused) append(if (isEmpty()) "Paused" else ". Paused") else append(if (isEmpty()) "${formatClock(state.remainingInStep)} left" else ", ${formatClock(state.remainingInStep)} left")
        }
        val open = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val b = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_workout)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setCategory(NotificationCompat.CATEGORY_WORKOUT)
            .setContentIntent(open)
            .setProgress(state.plan.totalSeconds, state.elapsedTotal.coerceAtMost(state.plan.totalSeconds), false)
            // if Android closes the app mid-workout, the notification goes away by itself instead of going stale
            .setTimeoutAfter(((state.plan.totalSeconds - state.elapsedTotal).coerceAtLeast(0) + if (paused) 1800 else 120) * 1000L)
        if (!paused) {
            b.setUsesChronometer(true).setChronometerCountDown(true)
                .setWhen(System.currentTimeMillis() + state.remainingInStep * 1000L).setShowWhen(true)
        }
        // Android 16: ask the system to promote this user-started activity to a Live Update (status-bar chip, lock screen).
        b.extras.putBoolean("android.requestPromotedOngoing", true)
        try {
            manager.notify(ID, b.build())
        } catch (_: SecurityException) {
            // permission withdrawn mid-session: the workout carries on without the notification
        }
    }

    fun clear() = manager.cancel(ID)

    companion object {
        /** A fresh app process has no workout running: drop a notification left behind by a closed one. */
        fun clearStale(context: Context) = NotificationManagerCompat.from(context).cancel(ID)
    }

    private fun ensureChannel() {
        val nm = context.getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL, "Workout in progress", NotificationManager.IMPORTANCE_LOW).apply {
                    description = "The current move and time left while a workout runs."
                    setShowBadge(false)
                },
            )
        }
    }

}

private const val CHANNEL = "workout"
private const val ID = 4201

/**
 * Headphone and earbud buttons while a workout runs: play/pause pauses or resumes, next skips. Uses the platform media
 * session, so whether the buttons reach the app depends on the phone and headset.
 */
class WorkoutButtons(context: Context, private val onToggle: () -> Unit, private val onNext: () -> Unit) {
    private val session = MediaSession(context, "MOTIONFORGE workout").apply {
        setCallback(object : MediaSession.Callback() {
            override fun onPlay() = onToggle()
            override fun onPause() = onToggle()
            override fun onSkipToNext() = onNext()
        })
        isActive = true
    }

    fun setPlaying(playing: Boolean) {
        session.setPlaybackState(
            PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_SKIP_TO_NEXT)
                .setState(if (playing) PlaybackState.STATE_PLAYING else PlaybackState.STATE_PAUSED, PlaybackState.PLAYBACK_POSITION_UNKNOWN, 1f)
                .build(),
        )
    }

    fun release() = session.release()
}
