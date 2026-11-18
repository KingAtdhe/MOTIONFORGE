package eu.motionforge.app.core.render3d

import android.annotation.SuppressLint
import android.content.Context
import android.view.Choreographer
import android.view.SurfaceView
import android.view.View
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.google.android.filament.utils.ModelViewer
import com.google.android.filament.utils.Utils
import java.nio.ByteBuffer
import java.nio.ByteOrder

data class AnimationClip(val index: Int, val name: String, val durationSeconds: Float)

sealed interface GlbLoadState {
    data object Loading : GlbLoadState
    data class Loaded(val clips: List<AnimationClip>) : GlbLoadState
    data class Failed(val reason: String) : GlbLoadState
}

/**
 * Playback controls shared between the Compose UI and the render loop.
 * All reads/writes happen on the main thread.
 */
class GlbPlayback {
    var loadState: GlbLoadState by mutableStateOf(GlbLoadState.Loading)
        internal set
    var playing: Boolean by mutableStateOf(true)
    var speed: Float by mutableStateOf(1f)
    var clipIndex: Int by mutableStateOf(0)
        private set

    internal var timeSeconds: Double = 0.0

    fun selectClip(index: Int) {
        clipIndex = index
        timeSeconds = 0.0
    }

    fun replay() {
        timeSeconds = 0.0
        playing = true
    }
}

private object FilamentRuntime {
    /** Loads Filament native libraries once. Returns a failure instead of crashing. */
    val initResult: Result<Unit> by lazy { runCatching { Utils.init() } }
}

/**
 * Renders a bundled GLB with Filament's gltfio [ModelViewer] and plays its named
 * animation clips. If Filament or the asset fails, [GlbPlayback.loadState] becomes
 * [GlbLoadState.Failed] and the caller shows its static fallback — the app never crashes
 * because a model failed to load.
 */
@SuppressLint("ClickableViewAccessibility")
@Composable
fun GlbModelView(
    assetPath: String,
    playback: GlbPlayback,
    modifier: Modifier = Modifier,
    allowOrbit: Boolean = true,
    backgroundRgb: FloatArray = floatArrayOf(0.055f, 0.067f, 0.078f),
) {
    AndroidView(
        modifier = modifier,
        factory = { context ->
            val surfaceView = SurfaceView(context)
            FilamentRuntime.initResult.exceptionOrNull()?.let {
                playback.loadState = GlbLoadState.Failed("3D renderer unavailable on this device: ${it.message}")
                return@AndroidView surfaceView
            }
            try {
                val viewer = ModelViewer(surfaceView)
                if (allowOrbit) {
                    surfaceView.setOnTouchListener { _, event ->
                        viewer.onTouchEvent(event)
                        true
                    }
                }
                viewer.renderer.clearOptions = viewer.renderer.clearOptions.apply {
                    clear = true
                    clearColor = floatArrayOf(backgroundRgb[0], backgroundRgb[1], backgroundRgb[2], 1f)
                }
                viewer.loadModelGlb(readAsset(context, assetPath))
                viewer.transformToUnitCube()

                val animator = viewer.animator
                val clips = if (animator == null) emptyList() else (0 until animator.animationCount).map { i ->
                    AnimationClip(i, animator.getAnimationName(i) ?: "clip_$i", animator.getAnimationDuration(i))
                }
                playback.loadState = GlbLoadState.Loaded(clips)

                val loop = RenderLoop(viewer, playback)
                surfaceView.addOnAttachStateChangeListener(object : View.OnAttachStateChangeListener {
                    override fun onViewAttachedToWindow(v: View) = loop.start()
                    override fun onViewDetachedFromWindow(v: View) = loop.stop()
                })
                if (surfaceView.isAttachedToWindow) loop.start()
            } catch (t: Throwable) {
                playback.loadState = GlbLoadState.Failed("Could not load 3D demo: ${t.message ?: t.javaClass.simpleName}")
            }
            surfaceView
        },
    )
}

private fun readAsset(context: Context, path: String): ByteBuffer {
    val bytes = context.assets.open(path).use { it.readBytes() }
    val buffer = ByteBuffer.allocateDirect(bytes.size).order(ByteOrder.nativeOrder())
    buffer.put(bytes)
    buffer.flip()
    return buffer
}

private class RenderLoop(
    private val viewer: ModelViewer,
    private val playback: GlbPlayback,
) : Choreographer.FrameCallback {
    private val choreographer = Choreographer.getInstance()
    private var running = false
    private var lastFrameNanos = 0L

    fun start() {
        if (running) return
        running = true
        lastFrameNanos = 0L
        choreographer.postFrameCallback(this)
    }

    fun stop() {
        running = false
        choreographer.removeFrameCallback(this)
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running) return
        choreographer.postFrameCallback(this)
        val dt = if (lastFrameNanos == 0L) 0.0 else (frameTimeNanos - lastFrameNanos) / 1_000_000_000.0
        lastFrameNanos = frameTimeNanos
        if (playback.playing) playback.timeSeconds += dt * playback.speed

        viewer.animator?.let { animator ->
            val clip = playback.clipIndex
            if (clip in 0 until animator.animationCount) {
                val duration = animator.getAnimationDuration(clip)
                val t = if (duration > 0f) (playback.timeSeconds % duration).toFloat() else 0f
                animator.applyAnimation(clip, t)
                animator.updateBoneMatrices()
            }
        }
        viewer.render(frameTimeNanos)
    }
}
