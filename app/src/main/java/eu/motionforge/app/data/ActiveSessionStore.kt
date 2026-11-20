package eu.motionforge.app.data

import android.content.Context
import eu.motionforge.app.feature.session.SessionSnapshot
import java.io.File

/**
 * The one unfinished session, kept in app-private storage (not backed up, not shared) so a workout survives Android
 * closing the app. Small synchronous file I/O: callers use a background dispatcher for writes.
 */
class ActiveSessionStore(context: Context) {
    private val file = File(context.applicationContext.noBackupFilesDir, "active_session.json")
    private val lock = Any()

    /** Bumped by every [clear]; a write made for an older epoch is dropped, so a slow background write can never
     *  bring back a session that was just saved, discarded or replaced. */
    @Volatile
    var epoch: Int = 0
        private set

    fun read(nowMillis: Long = System.currentTimeMillis()): SessionSnapshot? = synchronized(lock) {
        val text = runCatching { if (file.isFile) file.readText() else null }.getOrNull() ?: return null
        val snap = SessionSnapshot.decode(text)
        if (snap == null || snap.isExpired(nowMillis)) {
            file.delete()
            null
        } else {
            snap
        }
    }

    fun write(snapshot: SessionSnapshot, forEpoch: Int) = synchronized(lock) {
        if (forEpoch != epoch) return
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeText(SessionSnapshot.encode(snapshot))
        if (!tmp.renameTo(file)) {
            file.delete()
            tmp.renameTo(file)
        }
    }

    fun clear() = synchronized(lock) {
        epoch++
        file.delete()
        Unit
    }
}
