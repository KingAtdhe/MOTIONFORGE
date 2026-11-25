package eu.motionforge.app.core.render3d

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

/** The coach model is read once and handed out as independent read views (each 3D view gets its own position). */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class GlbBytesTest {
    @Test
    fun sharedBytesAreDirectIndependentAndStartAtTheGlbHeader() {
        val ctx = RuntimeEnvironment.getApplication()
        val a = GlbBytes.get(ctx, "models/coach_f.glb")
        a.position(100)                                     // one viewer reading must not move the next one's start
        val b = GlbBytes.get(ctx, "models/coach_f.glb")
        assertTrue(b.isDirect)
        assertEquals(0, b.position())
        assertEquals(a.capacity(), b.limit())
        assertEquals("glTF magic", 0x46546C67, b.getInt(0))
    }
}
