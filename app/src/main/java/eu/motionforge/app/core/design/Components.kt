package eu.motionforge.app.core.design

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import eu.motionforge.app.core.pose.TrackingState
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.ui.text.style.TextAlign

// ---------------------------------------------------------------------------------------------- surfaces

private val Cut = RoundedCornerShape(2.dp)

/** A quiet block for notes: a lighter sheet on the concrete page, square-cut. Clickable only when [onClick] is given. */
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
            shape = Cut,
            color = bg,
            content = inner,
        )
    } else {
        Surface(modifier = modifier.fillMaxWidth(), shape = Cut, color = bg, content = inner)
    }
}

/** Small label for a block ("Safety"). Sentence case. */
@Composable
fun Eyebrow(text: String, color: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Text(text, style = MaterialTheme.typography.labelLarge, color = color)
}

/** The heavy black rule that opens every section, like a printed programme. */
@Composable
fun HeavyRule(modifier: Modifier = Modifier, color: Color = MaterialTheme.colorScheme.onBackground) {
    Box(modifier.fillMaxWidth().height(3.dp).background(color))
}

/** Thin rule between rows. */
@Composable
fun ThinRule(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(MaterialTheme.colorScheme.outline))
}

/** Section opener: a heavy rule, then the title in the wide face, with an optional link on the right ("See all"). */
@Composable
fun SectionHeader(title: String, trailing: String? = null, trailingColor: Color = MaterialTheme.colorScheme.onBackground, onTrailing: (() -> Unit)? = null) {
    Column(Modifier.fillMaxWidth().padding(top = 18.dp)) {
        HeavyRule()
        Row(Modifier.fillMaxWidth().padding(top = 10.dp)) {
            Text(title, style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onBackground, modifier = Modifier.weight(1f).alignByBaseline().semantics { heading() })
            if (trailing != null) {
                val clickable = if (onTrailing != null) {
                    Modifier.clickable(role = Role.Button, onClick = onTrailing).padding(start = 12.dp, top = 12.dp, bottom = 12.dp)
                } else Modifier
                Text(
                    trailing,
                    color = trailingColor,
                    style = MaterialTheme.typography.labelLarge.copy(textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline),
                    modifier = Modifier.alignByBaseline().then(clickable),
                )
            }
        }
    }
}

/** A small filled square that marks a lesson's kind next to its text label (never alone). */
@Composable
fun KindMark(color: Color, modifier: Modifier = Modifier) {
    Box(modifier.size(10.dp).background(color))
}

// ---------------------------------------------------------------------------------------------- status

/**
 * Tracking status chip. Uses a text label and a shape marker as well as colour, so status is never conveyed by
 * colour alone. Lives over the camera picture.
 */
@Composable
fun TrackingStatusChip(state: TrackingState, modifier: Modifier = Modifier) {
    val (color, marker) = when (state) {
        TrackingState.TRACKING -> MfColors.SignalOnNight to "●"
        TrackingState.CALIBRATING, TrackingState.CAMERA_INITIALIZING, TrackingState.PAUSED -> MfColors.OnNightMuted to "◐"
        TrackingState.CAMERA_ERROR, TrackingState.CAMERA_PERMISSION_DENIED -> MfColors.Halt to "■"
        else -> MfColors.CautionOnNight to "▲"
    }
    Surface(modifier = modifier, shape = RoundedCornerShape(50), color = Color.Black.copy(alpha = 0.72f)) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(marker, color = color, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(8.dp))
            Text(state.userMessage, color = MfColors.OnNight, style = MaterialTheme.typography.labelLarge)
        }
    }
}

// ---------------------------------------------------------------------------------------------- choices

/** A two-state choice (filters, small pickers): black when on, outlined when off. */
@Composable
fun ChoiceButton(label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val ink = MaterialTheme.colorScheme.onBackground
    Surface(
        modifier = modifier.heightIn(min = 44.dp).selectable(selected = selected, onClick = onClick, role = Role.Checkbox),
        shape = Cut,
        color = if (selected) ink else Color.Transparent,
        border = if (selected) null else BorderStroke(1.5.dp, ink),
    ) {
        Box(Modifier.padding(horizontal = 16.dp, vertical = 11.dp), contentAlignment = Alignment.Center) {
            Text(label, style = MaterialTheme.typography.labelLarge, color = if (selected) MaterialTheme.colorScheme.background else ink)
        }
    }
}

/** Large single-choice option (onboarding): a square box that fills black when chosen. */
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
        shape = Cut,
        color = if (selected) MaterialTheme.colorScheme.surfaceContainer else Color.Transparent,
        border = BorderStroke(if (selected) 3.dp else 1.dp, if (selected) ink else MaterialTheme.colorScheme.outline),
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleLarge, color = ink)
                Text(description, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(Modifier.width(12.dp))
            Box(
                Modifier.size(22.dp).border(2.dp, ink).padding(4.dp).background(if (selected) ink else Color.Transparent),
            )
        }
    }
}

/** Single-choice tabs (category, speed, camera angle, filters): plain words, the chosen one underlined in heavy black. */
@Composable
fun SegmentedPill(
    options: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
    accent: Color = MaterialTheme.colorScheme.onBackground,
    compact: Boolean = false,
) {
    val ink = MaterialTheme.colorScheme.onBackground
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(if (compact) 14.dp else 18.dp)) {
        options.forEachIndexed { i, label ->
            val selected = i == selectedIndex
            Column(
                Modifier
                    .heightIn(min = 44.dp)
                    .selectable(selected = selected, onClick = { onSelect(i) }, role = Role.RadioButton)
                    .padding(top = 10.dp),
                horizontalAlignment = Alignment.Start,
            ) {
                Text(
                    label,
                    style = if (compact) MaterialTheme.typography.labelLarge else MaterialTheme.typography.titleLarge,
                    color = if (selected) ink else MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(6.dp))
                Box(Modifier.height(3.dp).width(if (selected) 24.dp else 0.dp).background(ink))
            }
        }
    }
}

/** Small read-only fact, e.g. "60 s": plain secondary text. */
@Composable
fun FactChip(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

// ---------------------------------------------------------------------------------------------- actions

/** Full-width main action: a square-cut black bar with the label set left, like a ticket. */
@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    color: Color = MaterialTheme.colorScheme.primary,
    trailing: String? = null,
) {
    val fg = if (color == MfColors.Blaze) Color.Black else MaterialTheme.colorScheme.onPrimary
    androidx.compose.material3.Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().heightIn(min = 60.dp),
        shape = Cut,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 20.dp),
        colors = androidx.compose.material3.ButtonDefaults.buttonColors(
            containerColor = color,
            contentColor = fg,
            disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
        ),
    ) {
        Text(text, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
        if (trailing != null) Text(trailing, style = MaterialTheme.typography.titleMedium)
    }
}

/** Large square action with a text label underneath (workout controls). */
@Composable
fun RoundAction(
    symbol: String,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    container: Color = MaterialTheme.colorScheme.surfaceVariant,
    content: Color = MaterialTheme.colorScheme.onSurface,
    size: Dp = 56.dp,
) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Surface(
            onClick = onClick,
            modifier = Modifier.width(size).height(size).semantics { contentDescription = label; role = Role.Button },
            shape = Cut,
            color = container,
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(symbol, style = MaterialTheme.typography.titleLarge, color = content, modifier = Modifier.clearAndSetSemantics {})
            }
        }
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.clearAndSetSemantics {})
    }
}

// ---------------------------------------------------------------------------------------------- numbers

/** Big narrow number with a plain caption under it; no box. */
@Composable
fun StatTile(value: String, label: String, modifier: Modifier = Modifier, accent: Color = MaterialTheme.colorScheme.onSurface) {
    Column(modifier.padding(vertical = 4.dp)) {
        Text(value, style = MfType.Numeral, color = accent)
        Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Ring that empties as a step counts down, with the time in the middle. [fraction] = time left / step length. */
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
            val stroke = size.minDimension * 0.06f
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

// ---------------------------------------------------------------------------------------------- lessons

/** A lesson as a picture and a caption: the coach in its colour field, name and length under it. */
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
    Surface(onClick = onClick, modifier = modifier.semantics { role = Role.Button }, shape = Cut, color = Color.Transparent) {
        Column {
            Box(Modifier.fillMaxWidth().height(artHeight).background(accent)) {
                StageFloor(accent, Modifier.align(Alignment.BottomCenter))
                CoachArt(artPath, Modifier.fillMaxSize().padding(top = 12.dp, bottom = 4.dp))
                if (badge != null) {
                    Text(
                        badge,
                        Modifier.align(Alignment.TopStart).padding(10.dp),
                        style = MaterialTheme.typography.labelLarge,
                        color = onField(accent),
                    )
                }
            }
            Column(Modifier.padding(top = 10.dp, bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis, color = MaterialTheme.colorScheme.onBackground)
                Text(meta, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
            }
        }
    }
}

/**
 * A lesson as one line of the programme: the coach in a small colour field, the name, a note, and the length in the
 * narrow numerals on the right. The whole row is one button.
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
    Row(
        modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = onClick)
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.width(76.dp).height(92.dp).background(accent)) {
            CoachArt(artPath, Modifier.fillMaxSize().padding(top = 4.dp, bottom = 2.dp))
        }
        Column(Modifier.weight(1f).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(note, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Text(length, style = MfType.NumeralSmall, textAlign = TextAlign.End)
    }
}

/** The coach (a still or the live 3D coach) standing in the lesson's colour field. */
@Composable
fun CoachStage(
    name: String,
    accent: Color,
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(modifier.background(accent)) {
        StageFloor(accent, Modifier.align(Alignment.BottomCenter))
        content()
    }
}

/** The colour field behind the coach: flat, no gradient. */
@Composable
fun stageBrush(accent: Color): Brush = androidx.compose.ui.graphics.SolidColor(accent)

/** Soft contact shadow so the coach stands on the floor instead of floating. */
@Suppress("UNUSED_PARAMETER")
@Composable
fun StageFloor(accent: Color, modifier: Modifier = Modifier) {
    Box(
        modifier
            .padding(bottom = 10.dp)
            .fillMaxWidth(0.55f)
            .height(20.dp)
            .clip(androidx.compose.foundation.shape.GenericShape { size, _ -> addOval(androidx.compose.ui.geometry.Rect(0f, 0f, size.width, size.height)) })
            .background(Brush.radialGradient(listOf(Color.Black.copy(alpha = 0.28f), Color.Transparent))),
    )
}

fun formatClock(totalSeconds: Int): String {
    val s = totalSeconds.coerceAtLeast(0)
    return "%d:%02d".format(s / 60, s % 60)
}

/** "2 min" for ≥ 60 s, else "45 s". */
fun formatLength(seconds: Int): String = if (seconds >= 60) "${(seconds + 30) / 60} min" else "$seconds s"
