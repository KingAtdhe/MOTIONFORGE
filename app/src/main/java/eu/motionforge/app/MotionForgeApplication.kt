package eu.motionforge.app

import android.app.Application
import android.content.Context
import eu.motionforge.app.data.ActiveSessionStore
import eu.motionforge.app.data.ClipManifestRepository
import eu.motionforge.app.data.ExerciseRepository
import eu.motionforge.app.data.SessionRepository
import eu.motionforge.app.data.UserPreferencesRepository

/** Manual dependency container. Small enough that a DI framework is not yet justified. */
class AppContainer(context: Context) {
    val exercises: ExerciseRepository by lazy { ExerciseRepository(context) }
    val preferences: UserPreferencesRepository by lazy { UserPreferencesRepository(context) }
    val sessions: SessionRepository by lazy { SessionRepository(context) }
    val clips: ClipManifestRepository by lazy { ClipManifestRepository(context) }
    val activeSession: ActiveSessionStore by lazy { ActiveSessionStore(context) }
}

class MotionForgeApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        eu.motionforge.app.feature.session.WorkoutNotifier.clearStale(this)
    }
}
