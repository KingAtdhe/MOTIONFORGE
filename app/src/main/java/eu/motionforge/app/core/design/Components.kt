package eu.motionforge.app.core.design

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.pose.TrackingState

/** Plates and the action bar: a trimmed photo print's corner. */
val PlateShape = RoundedCornerShape(6.dp)

// ---------------------------------------------------------------------------------------------- surfaces

/** A quiet sheet on the silver page for notes and settings. Clickable only when [onClick] is given. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val inner: @Composable () -> Unit = {
        Column(Modifier.padding(horizontal = 18.dp, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(6.dp), content = content)
    }
    val bg = MaterialTheme.colorScheme.surfaceContainer
    if (onClick != null) {
        Surface(
            onClick = onClick,
            modifier = modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { role = Role.Button },
            shape = PlateShape,
            color = bg,
            content = inner,
        )
    } else {
        Surface(modifier = modifier.fillMaxWidth(), shape = PlateShape, color = bg, content = inner)
    }
}

/** Small label for a block ("Safety"). Sentence case. */
@Composable
fun Eyebrow(text: String, color: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Text(text, style = MaterialTheme.typography.labelLarge, color = color)
}

/** Kept for older call sites: a plain rule. */
@Composable
fun HeavyRule(modifier: Modifier = Modifier, color: Color = MaterialTheme.colorScheme.outline) {
    Box(modifier.fillMaxWidth().height(1.dp).background(color))
}

/** Thin rule between rows. */
@Composable
fun ThinRule(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(MaterialTheme.colorScheme.outline))
}

/** Section head: the title, with an optional link on the right ("See all"). */
@Composable
fun SectionHeader(title: String, trailing: String? = null, trailingColor: Color = MaterialTheme.colorScheme.onSurfaceVariant, onTrailing: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth().padding(top = 14.dp)) {
        Text(title, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onBackground, modifier = Modifier.weight(1f).alignByBaseline().semantics { heading() })
        if (trailing != null) {
            val clickable = if (onTrailing != null) {
                Modifier.clickable(role = Role.Button, onClick = onTrailing).padding(start = 12.dp, top = 12.dp, bottom = 12.dp)
            } else Modifier
            Text(
                trailing,
                color = if (onTrailing != null) MaterialTheme.colorScheme.onBackground else trailingColor,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.alignByBaseline().then(clickable),
            )
        }
    }
}

/** Kept for older call sites. */
@Composable
fun KindMark(color: Color, modifier: Modifier = Modifier) {
    Box(modifier.size(8.dp).background(color, CircleShape))
}

// ---------------------------------------------------------------------------------------------- status

/** Tracking status over the camera picture: a text label and a shape marker as well as colour. */
@Composable
fun TrackingStatusChip(state: TrackingState, modifier: Modifier = Modifier) {
    val (color, marker) = when (state) {
        TrackingState.TRACKING -> MfColors.SignalOnNight to "●"
        TrackingState.CALIBRATING, TrackingState.CAMERA_INITIALIZING, TrackingState.PAUSED -> MfColors.OnNightMuted to "◐"
        TrackingState.CAMERA_ERROR, TrackingState.CAMERA_PERMISSION_DENIED -> MfColors.Halt to "■"
        else -> MfColors.CautionOnNight to "▲"
    }
    Surface(modifier = modifier, shape = PlateShape, color = Color.Black.copy(alpha = 0.72f)) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(marker, color = color, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(8.dp))
            Text(state.userMessage, color = MfColors.OnNight, style = MaterialTheme.typography.labelLarge)
        }
    }
}

// ---------------------------------------------------------------------------------------------- choices

/** A two-state choice (filters): ink when on, outlined when off. */
@Composable
fun ChoiceButton(label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val ink = MaterialTheme.colorScheme.onBackground
    Surface(
        modifier = modifier.heightIn(min = 44.dp).selectable(selected = selected, onClick = onClick, role = Role.Checkbox),
        shape = PlateShape,
        color = if (selected) ink else Color.Transparent,
        border = if (selected) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Box(Modifier.padding(horizontal = 16.dp, vertical = 11.dp), contentAlignment = Alignment.Center) {
            Text(label, style = MaterialTheme.typography.labelLarge, color = if (selected) MaterialTheme.colorScheme.background else ink)
        }
    }
}

/** Large single-choice option (onboarding): a sheet that gains an ink outline and a filled dot when chosen. */
@Composable
fun SelectableOption(
    title: String,
    description: String,
    selected: Boolean,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val ink = MaterialTheme.colorScheme.onBackground
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 64.dp)
            .selectable(selected = selected, onClick = onSelect, role = Role.RadioButton),
        shape = PlateShape,
        color = MaterialTheme.colorScheme.surfaceContainer,
        border = if (selected) BorderStroke(2.dp, ink) else null,
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleLarge, color = ink)
                Text(description, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(Modifier.width(12.dp))
            Box(
                Modifier.size(22.dp).border(2.dp, if (selected) ink else MaterialTheme.colorScheme.onSurfaceVariant, CircleShape).padding(5.dp)
                    .background(if (selected) ink else Color.Transparent, CircleShape),
            )
        }
    }
}

/** Single-choice segmented control: a sheet track, the chosen option in ink. */
@Composable
fun SegmentedPill(
    options: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
    accent: Color = MaterialTheme.colorScheme.onBackground,
    compact: Boolean = false,
) {
    Row(
        modifier.clip(PlateShape).background(MaterialTheme.colorScheme.surfaceContainerHighest).padding(3.dp),
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        options.forEachIndexed { i, label ->
            val selected = i == selectedIndex
            Box(
                Modifier
                    .heightIn(min = if (compact) 38.dp else 42.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(if (selected) MaterialTheme.colorScheme.onBackground else Color.Transparent)
                    .selectable(selected = selected, onClick = { onSelect(i) }, role = Role.RadioButton)
                    .padding(horizontal = if (compact) 12.dp else 16.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    label,
                    style = if (compact) MaterialTheme.typography.labelMedium else MaterialTheme.typography.labelLarge,
                    color = if (selected) MaterialTheme.colorScheme.background else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

/** Small read-only fact, e.g. "60 s". */
@Composable
fun FactChip(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

// ---------------------------------------------------------------------------------------------- actions

/**
 * The one action on a screen: a full-width timing-board yellow bar, 64 dp tall, black label on the left and an
 * optional figure (the session length) on the right. Meant for the bottom of the screen, under the thumb.
 */
@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    color: Color = MfColors.Yellow,
    trailing: String? = null,
) {
    val fg = if (color == MfColors.Yellow) Color.Black else Color.White
    androidx.compose.material3.Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().heightIn(min = 64.dp),
        shape = PlateShape,
        contentPadding = PaddingValues(horizontal = 22.dp),
        colors = androidx.compose.material3.ButtonDefaults.buttonColors(
            containerColor = color,
            contentColor = fg,
            disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
        ),
    ) {
        Text(text, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
        if (trailing != null) Text(trailing, style = MfType.NumeralSmall)
    }
}

/** A secondary action: outlined, same height family as the action bar. */
@Composable
fun SecondaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, color: Color = MaterialTheme.colorScheme.onBackground) {
    androidx.compose.material3.OutlinedButton(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().heightIn(min = 52.dp),
        shape = PlateShape,
        border = BorderStroke(1.dp, color.copy(alpha = 0.4f)),
        colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(contentColor = color),
    ) { Text(text, style = MaterialTheme.typography.titleMedium) }
}

/** Large square action with a text label underneath (workout controls when paused). */
@Composable
fun RoundAction(
    symbol: String,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    container: Color = MaterialTheme.colorScheme.surfaceVariant,
    content: Color = MaterialTheme.colorScheme.onSurface,
    size: Dp = 64.dp,
) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Surface(
            onClick = onClick,
            modifier = Modifier.width(size).height(size).semantics { contentDescription = label; role = Role.Button },
            shape = PlateShape,
            color = container,
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(symbol, style = MaterialTheme.typography.titleLarge, color = content, modifier = Modifier.clearAndSetSemantics {})
            }
        }
        Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.clearAndSetSemantics {})
    }
}

// ---------------------------------------------------------------------------------------------- numbers

/** Big condensed number with a plain caption under it; no box. */
@Composable
fun StatTile(value: String, label: String, modifier: Modifier = Modifier, accent: Color = MaterialTheme.colorScheme.onSurface) {
    Column(modifier.padding(vertical = 4.dp)) {
        Text(value, style = MfType.Numeral, color = accent)
        Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/**
 * The measuring scale from the foot of Marey's plates: a baseline with a tick every 1/40, a taller one every 1/8.
 * When [fraction] is given the run up to it is drawn in [fill] — the timer track during a workout.
 */
@Composable
fun MeasureScale(
    modifier: Modifier = Modifier,
    color: Color = MaterialTheme.colorScheme.onSurfaceVariant,
    fraction: Float? = null,
    fill: Color = MfColors.Yellow,
) {
    Canvas(modifier.fillMaxWidth().height(14.dp).clearAndSetSemantics {}) {
        val base = size.height - 1.dp.toPx()
        val f = fraction?.coerceIn(0f, 1f)
        if (f != null) drawRect(fill, topLeft = Offset(0f, base - 5.dp.toPx()), size = Size(size.width * f, 5.dp.toPx()))
        drawLine(color, Offset(0f, base), Offset(size.width, base), 1.dp.toPx())
        for (i in 0..40) {
            val x = size.width * i / 40f
            val tall = i % 5 == 0
            drawLine(color, Offset(x, base), Offset(x, base - (if (tall) 12.dp else 5.dp).toPx()), 1.dp.toPx())
        }
    }
}

/** Ring countdown, kept for older call sites. [fraction] = time left / step length. */
@Composable
fun CountdownRing(
    fraction: Float,
    label: String,
    accent: Color,
    modifier: Modifier = Modifier,
    caption: String? = null,
    dimmed: Boolean = false,
) {
    val track = MaterialTheme.colorScheme.surfaceVariant
    val muted = MaterialTheme.colorScheme.onSurfaceVariant
    Box(modifier, contentAlignment = Alignment.Center) {
        Canvas(Modifier.matchParentSize()) {
            val stroke = size.minDimension * 0.05f
            val arcSize = Size(size.minDimension - stroke, size.minDimension - stroke)
            val topLeft = Offset((size.width - arcSize.width) / 2, (size.height - arcSize.height) / 2)
            val style = Stroke(stroke, cap = StrokeCap.Butt)
            drawArc(track, -90f, 360f, false, topLeft, arcSize, style = style)
            drawArc(if (dimmed) muted else accent, -90f, 360f * fraction.coerceIn(0f, 1f), false, topLeft, arcSize, style = style)
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, style = MfType.Numeral, color = if (dimmed) muted else MaterialTheme.colorScheme.onSurface)
            if (caption != null) Text(caption, style = MaterialTheme.typography.labelMedium, color = muted)
        }
    }
}

// ---------------------------------------------------------------------------------------------- plates

/** A black plate with a lesson's motion study filling it. Decorative unless [description] is given. */
@Composable
fun MotionStudy(path: String, modifier: Modifier = Modifier, description: String? = null, crop: Boolean = false) {
    Box(modifier.clip(PlateShape).background(MfColors.Plate)) {
        CoachArt(
            path,
            Modifier.fillMaxSize(),
            contentDescription = description,
            contentScale = if (crop) ContentScale.Crop else ContentScale.Fit,
        )
    }
}

/** A lesson as a plate and a caption: its motion study, name and length under it. */
@Composable
fun LessonTile(
    title: String,
    meta: String,
    accent: Color,
    artPath: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    badge: String? = null,
    artHeight: Dp = 168.dp,
) {
    Surface(onClick = onClick, modifier = modifier.semantics { role = Role.Button }, shape = PlateShape, color = Color.Transparent) {
        Column {
            Box {
                MotionStudy(artPath, Modifier.fillMaxWidth().height(artHeight), crop = true)
                if (badge != null) {
                    Text(badge, Modifier.align(Alignment.TopStart).padding(10.dp), style = MaterialTheme.typography.labelLarge, color = Color.White)
                }
            }
            Column(Modifier.padding(top = 8.dp, bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis, color = MaterialTheme.colorScheme.onBackground)
                Text(meta, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
            }
        }
    }
}

/**
 * One row of the lesson contact sheet: name and time on top, then four frames of the movement on a black strip.
 * The whole row is one button; the strip is decorative (the name says what it is).
 */
@Composable
fun LessonRow(
    title: String,
    note: String,
    length: String,
    accent: Color,
    artPath: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = onClick)
            .padding(vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(note, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Text(length, style = MfType.NumeralSmall)
        }
        MotionStudy(artPath, Modifier.fillMaxWidth().height(92.dp), crop = true)
    }
}

/** The black stage the coach (a study or the live 3D coach) stands on. */
@Composable
fun CoachStage(
    name: String,
    accent: Color,
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(modifier.clip(PlateShape).background(MfColors.Plate), content = content)
}

/** The plate behind the coach: flat black. */
@Suppress("UNUSED_PARAMETER")
@Composable
fun stageBrush(accent: Color): Brush = SolidColor(MfColors.Plate)

/** No floor shadow on a black plate; kept for older call sites. */
@Suppress("UNUSED_PARAMETER")
@Composable
fun StageFloor(accent: Color, modifier: Modifier = Modifier) = Unit

fun formatClock(totalSeconds: Int): String {
    val s = totalSeconds.coerceAtLeast(0)
    return "%d:%02d".format(s / 60, s % 60)
}

/** "2 min" for ≥ 60 s, else "45 s". */
fun formatLength(seconds: Int): String = if (seconds >= 60) "${(seconds + 30) / 60} min" else "$seconds s"
