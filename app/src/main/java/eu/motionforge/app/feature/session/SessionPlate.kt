package eu.motionforge.app.feature.session

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Paint
import android.graphics.Typeface
import androidx.compose.foundation.Canvas
import androidx.compose.ui.Modifier
import androidx.compose.runtime.Composable
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.core.content.FileProvider
import androidx.core.content.res.ResourcesCompat
import eu.motionforge.app.R
import eu.motionforge.app.core.pose.POSE_CONNECTIONS
import eu.motionforge.app.core.pose.PoseFrame
import java.io.File

/**
 * Your own motion study: the last tracked poses of the workout drawn as one plate, earlier poses faint, the last one in
 * timing yellow — Marey's "geometric chronophotography", made from body points only. No camera image is kept.
 */
internal object PlateGeometry {
    private const val MIN_VIS = 0.5f

    /** Each pose as joint positions in a [w]x[h] box with [pad] margin (null = joint not trusted). */
    fun layout(frames: List<PoseFrame>, w: Float, h: Float, pad: Float): List<List<Offset?>> {
        val pts = frames.map { f ->
            f.landmarks.map { lm ->
                if (lm.visibility < MIN_VIS) null
                else Offset((if (f.previewMirrored) 1f - lm.x else lm.x) * f.imageWidth, lm.y * f.imageHeight)
            }
        }
        val all = pts.flatten().filterNotNull()
        if (all.isEmpty()) return emptyList()
        val minX = all.minOf { it.x }; val maxX = all.maxOf { it.x }
        val minY = all.minOf { it.y }; val maxY = all.maxOf { it.y }
        val s = minOf((w - 2 * pad) / (maxX - minX).coerceAtLeast(1f), (h - 2 * pad) / (maxY - minY).coerceAtLeast(1f))
        val ox = (w - (maxX - minX) * s) / 2f; val oy = (h - (maxY - minY) * s) / 2f
        return pts.map { pose -> pose.map { p -> p?.let { Offset(ox + (it.x - minX) * s, oy + (it.y - minY) * s) } } }
    }

    /** Opacity of exposure [i] of [n]: older poses fainter. */
    fun alpha(i: Int, n: Int): Float = if (i == n - 1) 1f else 0.16f + 0.5f * i / (n - 1).coerceAtLeast(1)
}

@Composable
fun SessionPlateCanvas(frames: List<PoseFrame>, modifier: Modifier = Modifier) {
    Canvas(modifier.semantics { contentDescription = "Your movement drawn as a motion study from ${frames.size} moments" }) {
        val poses = PlateGeometry.layout(frames, size.width, size.height, 28f)
        poses.forEachIndexed { i, pose ->
            val last = i == poses.lastIndex
            val c = if (last) Color(0xFFFFD60A) else Color.White.copy(alpha = PlateGeometry.alpha(i, poses.size))
            POSE_CONNECTIONS.forEach { (a, b) ->
                val pa = pose[a.index]; val pb = pose[b.index]
                if (pa != null && pb != null) drawLine(c, pa, pb, strokeWidth = if (last) 7f else 4f, cap = StrokeCap.Round)
            }
            if (last) pose.forEachIndexed { j, p -> if (p != null && j !in 1..10) drawCircle(Color.White, 6f, p) }
        }
    }
}

/** Renders the plate to a PNG in the app's cache and opens the share sheet. Only the drawing leaves the phone. */
fun shareSessionPlate(context: Context, frames: List<PoseFrame>, title: String, stats: String) {
    val w = 1080; val h = 1350
    val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
    val c = android.graphics.Canvas(bmp)
    c.drawColor(android.graphics.Color.BLACK)
    val poses = PlateGeometry.layout(frames, w.toFloat(), h - 260f, 90f)
    val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { strokeCap = Paint.Cap.ROUND; style = Paint.Style.STROKE }
    poses.forEachIndexed { i, pose ->
        val last = i == poses.lastIndex
        line.color = if (last) 0xFFFFD60A.toInt() else android.graphics.Color.argb((PlateGeometry.alpha(i, poses.size) * 255).toInt(), 255, 255, 255)
        line.strokeWidth = if (last) 12f else 7f
        POSE_CONNECTIONS.forEach { (a, b) ->
            val pa = pose[a.index]; val pb = pose[b.index]
            if (pa != null && pb != null) c.drawLine(pa.x, pa.y, pb.x, pb.y, line)
        }
    }
    // measuring scale and caption
    val ink = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0x99FFFFFF.toInt(); strokeWidth = 2f }
    val base = h - 230f
    c.drawLine(80f, base, w - 80f, base, ink)
    for (i in 0..40) { val x = 80f + (w - 160f) * i / 40f; c.drawLine(x, base, x, base - if (i % 5 == 0) 26f else 10f, ink) }
    val face = ResourcesCompat.getFont(context, R.font.barlow_semicond_bold) ?: Typeface.DEFAULT_BOLD
    val body = ResourcesCompat.getFont(context, R.font.barlow_regular) ?: Typeface.DEFAULT
    c.drawText(title, 80f, h - 140f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = android.graphics.Color.WHITE; textSize = 64f; typeface = face })
    c.drawText(stats, 80f, h - 80f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xCCFFFFFF.toInt(); textSize = 40f; typeface = body })
    c.drawText("MOTIONFORGE", w - 80f, h - 80f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xFFFFD60A.toInt(); textSize = 36f; typeface = face; textAlign = Paint.Align.RIGHT })
    val dir = File(context.cacheDir, "plates").apply { mkdirs() }
    val file = File(dir, "motionforge-plate.png")
    file.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    bmp.recycle()
    val uri = FileProvider.getUriForFile(context, context.packageName + ".plates", file)
    val send = Intent(Intent.ACTION_SEND).setType("image/png").putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    context.startActivity(Intent.createChooser(send, "Share your session plate").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
}
