package eu.motionforge.app.core.render3d

import android.annotation.SuppressLint
import android.content.Context
import android.view.Choreographer
import android.view.TextureView
import android.view.View
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.viewinterop.AndroidView
import com.google.android.filament.EntityManager
import com.google.android.filament.IndirectLight
import com.google.android.filament.LightManager
import com.google.android.filament.utils.ModelViewer
import com.google.android.filament.utils.Utils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.nio.ByteBuffer
import java.nio.ByteOrder

data class AnimationClip(val index: Int, val name: String, val durationSeconds: Float)

sealed interface GlbLoadState {
    data object Loading : GlbLoadState
    data class Loaded(val clips: List<AnimationClip>) : GlbLoadState
    data class Failed(val reason: String) : GlbLoadState
}

/**
 * Playback state shared by the Compose controls and the render loop (main thread only).
 * Plays a looping *sequence* of clips; a single clip is a sequence of one.
 */
class GlbPlayback(initiallyPlaying: Boolean = true) {
    var loadState: GlbLoadState by mutableStateOf(GlbLoadState.Loading)
        internal set
    var playing: Boolean by mutableStateOf(initiallyPlaying)
    var speed: Float by mutableFloatStateOf(1f)
    var viewAngle: ViewAngle by mutableStateOf(ViewAngle.FRONT)

    /** Clip names to play in order (resolved against the loaded asset). */
    var sequence: List<String> by mutableStateOf(emptyList())
        private set

    /** Index into [sequence] of the clip currently shown (updated only when it changes). */
    var currentStep: Int by mutableIntStateOf(0)
        internal set

    internal var timeSeconds: Double = 0.0

    fun playSequence(clips: List<String>) {
        sequence = clips
        currentStep = 0
        timeSeconds = 0.0
    }

    fun replay() {
        timeSeconds = 0.0
        currentStep = 0
        playing = true
    }
}

private object FilamentRuntime {
    /** Loads Filament native libraries once. A failure is reported, never thrown. */
    val initResult: Result<Unit> by lazy { runCatching { Utils.init() } }
}

/** Owns the Filament viewer for one composable instance. */
@SuppressLint("ClickableViewAccessibility")
private class FilamentScene(context: Context, allowOrbit: Boolean, lit: Boolean, background: FloatArray) {
    val textureView = TextureView(context)
    val viewer: ModelViewer = ModelViewer(textureView)
    private val baseTransform = FloatArray(16)
    private var appliedYaw = Float.NaN
    var clips: List<AnimationClip> = emptyList()
        private set

    init {
        if (allowOrbit) {
            textureView.setOnTouchListener { _, event ->
                viewer.onTouchEvent(event)
                true
            }
        }
        viewer.renderer.clearOptions = viewer.renderer.clearOptions.apply {
            clear = true
            clearColor = floatArrayOf(background[0], background[1], background[2], 1f)
        }
        if (lit) addStudioLighting()
    }

    /**
     * Soft studio light without an environment texture: constant spherical-harmonics ambient plus a
     * frontal key light (ModelViewer already adds an overhead sun). Intensities are first estimates
     * and must be tuned on real devices.
     */
    private fun addStudioLighting() {
        val engine = viewer.engine
        val ambient = IndirectLight.Builder()
            .irradiance(1, floatArrayOf(0.9f, 0.92f, 0.95f))
            .intensity(22_000f)
            .build(engine)
        viewer.scene.indirectLight = ambient
        val key = EntityManager.get().create()
        LightManager.Builder(LightManager.Type.DIRECTIONAL)
            .color(1.0f, 0.97f, 0.93f)
            .intensity(45_000f)
            .direction(0.35f, -0.45f, -1.0f)
            .castShadows(false)
            .build(engine, key)
        viewer.scene.addEntity(key)
        // rim light from behind: separates the lit (normal-mapped) coach from the background
        val rim = EntityManager.get().create()
        LightManager.Builder(LightManager.Type.DIRECTIONAL)
            .color(1.0f, 0.95f, 0.92f)
            .intensity(30_000f)
            .direction(-0.5f, -0.3f, 1.0f)
            .castShadows(false)
            .build(engine, rim)
        viewer.scene.addEntity(rim)
    }

    /** Must run on the main thread. */
    fun load(buffer: ByteBuffer) {
        viewer.loadModelGlb(buffer)
        viewer.transformToUnitCube()
        val asset = viewer.asset ?: error("GLB parsed but produced no asset")
        val tm = viewer.engine.transformManager
        tm.getTransform(tm.getInstance(asset.root), baseTransform)
        appliedYaw = Float.NaN
        val animator = viewer.animator
        clips = if (animator == null) emptyList() else (0 until animator.animationCount).map { i ->
            AnimationClip(i, animator.getAnimationName(i), animator.getAnimationDuration(i))
        }
    }

    fun applyYaw(yawDegrees: Float) {
        if (yawDegrees == appliedYaw) return
        val asset = viewer.asset ?: return
        val out = FloatArray(16)
        android.opengl.Matrix.rotateM(out, 0, baseTransform, 0, yawDegrees, 0f, 1f, 0f)
        val tm = viewer.engine.transformManager
        tm.setTransform(tm.getInstance(asset.root), out)
        appliedYaw = yawDegrees
    }
}

/**
 * Renders a bundled GLB with Filament's gltfio [ModelViewer] in a TextureView (scrolls cleanly
 * inside Compose layouts). The GLB is read off the main thread. If Filament or the asset fails,
 * [GlbPlayback.loadState] becomes [GlbLoadState.Failed] and the caller shows its text fallback.
 */
@Composable
fun GlbModelView(
    assetPath: String,
    playback: GlbPlayback,
    modifier: Modifier = Modifier,
    allowOrbit: Boolean = false,
    lit: Boolean = true,
    contentDescription: String = "3D demonstration",
    backgroundRgb: FloatArray = floatArrayOf(0.086f, 0.106f, 0.125f),
) {
    val context = LocalContext.current
    val sceneResult: Result<FilamentScene> = remember {
        FilamentRuntime.initResult.fold(
            onSuccess = { runCatching { FilamentScene(context, allowOrbit, lit, backgroundRgb) } },
            onFailure = { Result.failure(it) },
        )
    }
    val scene = sceneResult.getOrNull()
    if (scene == null) {
        LaunchedEffect(sceneResult) {
            playback.loadState = GlbLoadState.Failed(
                "3D renderer unavailable on this device (${sceneResult.exceptionOrNull()?.message}).",
            )
        }
        return
    }

    LaunchedEffect(scene, assetPath) {
        playback.loadState = GlbLoadState.Loading
        val buffer = try {
            withContext(Dispatchers.IO) { readAsset(context, assetPath) }
        } catch (e: Exception) {
            playback.loadState = GlbLoadState.Failed("3D model file could not be read (${e.message}).")
            return@LaunchedEffect
        }
        playback.loadState = try {
            scene.load(buffer)
            GlbLoadState.Loaded(scene.clips)
        } catch (t: Throwable) {
            GlbLoadState.Failed("3D model could not be loaded (${t.message ?: t.javaClass.simpleName}).")
        }
    }

    val loop = remember(scene) { RenderLoop(scene, playback) }
    DisposableEffect(loop) {
        val listener = object : View.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(v: View) = loop.start()
            override fun onViewDetachedFromWindow(v: View) = loop.stop()
        }
        scene.textureView.addOnAttachStateChangeListener(listener)
        if (scene.textureView.isAttachedToWindow) loop.start()
        onDispose {
            loop.stop()
            scene.textureView.removeOnAttachStateChangeListener(listener)
        }
    }

    AndroidView(
        factory = { scene.textureView },
        modifier = modifier.semantics { this.contentDescription = contentDescription },
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
    private val scene: FilamentScene,
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

        val viewer = scene.viewer
        if (viewer.asset != null) {
            scene.applyYaw(playback.viewAngle.yawDegrees)
            val animator = viewer.animator
            val clips = scene.clips
            val indices = playback.sequence.mapNotNull { name -> clips.firstOrNull { it.name == name }?.index }
            if (animator != null && indices.isNotEmpty()) {
                val durations = indices.map { animator.getAnimationDuration(it).coerceAtLeast(MIN_CLIP) }
                val (step, local) = DemoSequence.locate(durations, playback.timeSeconds)
                if (playback.currentStep != step) playback.currentStep = step
                animator.applyAnimation(indices[step], local)
                animator.updateBoneMatrices()
            }
        }
        viewer.render(frameTimeNanos)
    }

    private companion object {
        const val MIN_CLIP = 0.001f
    }
}
