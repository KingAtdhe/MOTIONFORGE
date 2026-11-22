package eu.motionforge.app.core.design

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
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

// ---------------------------------------------------------------------------------------------- surfaces

/** Graphite surface with a hairline edge for a block of content. Clickable only when [onClick] is given. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(20.dp)
    val edge = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    val inner: @Composable () -> Unit = {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 18.dp), verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
    if (onClick != null) {
        Surface(
            onClick = onClick,
            modifier = modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { role = Role.Button },
            shape = shape,
            color = MaterialTheme.colorScheme.surface,
            border = edge,
            content = inner,
        )
    } else {
        Surface(modifier = modifier.fillMaxWidth(), shape = shape, color = MaterialTheme.colorScheme.surface, border = edge, content = inner)
    }
}

/** Small section label: uppercase, letter-spaced, quiet ("SAFETY"). Screen readers get the original casing. */
@Composable
fun Eyebrow(text: String, color: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Text(
        text.uppercase(),
        style = MaterialTheme.typography.labelSmall,
        color = color,
        modifier = Modifier.semantics { contentDescription = text },
    )
}

/** Heading for a block of the page, optionally with an action on the right ("See all"). */
@Composable
fun SectionHeader(title: String, trailing: String? = null, trailingColor: Color = MaterialTheme.colorScheme.primary, onTrailing: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(title, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onBackground, modifier = Modifier.weight(1f).semantics { heading() })
        if (trailing != null) {
            if (onTrailing != null) {
                androidx.compose.material3.TextButton(onClick = onTrailing) { Text(trailing, color = trailingColor, style = MaterialTheme.typography.labelLarge) }
            } else {
                Text(trailing, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

// ---------------------------------------------------------------------------------------------- status

/**
 * Tracking status chip. Uses a text label and a shape marker as well as colour, so status is never conveyed by
 * colour alone. Lives on the dark workout scheme.
 */
@Composable
fun TrackingStatusChip(state: TrackingState, modifier: Modifier = Modifier) {
    val (color, marker) = when (state) {
        TrackingState.TRACKING -> MfColors.SignalOnNight to "●"
        TrackingState.CALIBRATING, TrackingState.CAMERA_INITIALIZING, TrackingState.PAUSED -> MfColors.OnNightMuted to "◐"
        TrackingState.CAMERA_ERROR, TrackingState.CAMERA_PERMISSION_DENIED -> Color(0xFFFF6B6B) to "■"
        else -> MfColors.CautionOnNight to "▲"
    }
    Surface(modifier = modifier, shape = RoundedCornerShape(50), color = MfColors.Night.copy(alpha = 0.82f), border = BorderStroke(1.dp, MfColors.NightRule)) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(marker, color = color, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(8.dp))
            Text(state.userMessage, color = MfColors.OnNight, style = MaterialTheme.typography.labelLarge)
        }
    }
}

// ---------------------------------------------------------------------------------------------- choices

/** A two-state choice button (filters, small pickers). Exposes its selected state to accessibility services. */
@Composable
fun ChoiceButton(label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.heightIn(min = 44.dp).selectable(selected = selected, onClick = onClick, role = Role.Checkbox),
        shape = RoundedCornerShape(50),
        color = if (selected) MaterialTheme.colorScheme.onSurface else Color.Transparent,
        border = if (selected) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Box(Modifier.padding(horizontal = 16.dp, vertical = 11.dp), contentAlignment = Alignment.Center) {
            Text(label, style = MaterialTheme.typography.labelLarge, color = if (selected) MaterialTheme.colorScheme.surface else MaterialTheme.colorScheme.onSurface)
        }
    }
}

/** Large radio-style option used in onboarding. */
@Composable
fun SelectableOption(
    title: String,
    description: String,
    selected: Boolean,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 64.dp)
            .selectable(selected = selected, onClick = onSelect, role = Role.RadioButton),
        shape = RoundedCornerShape(18.dp),
        color = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.material3.RadioButton(
                selected = selected,
                onClick = null,
                colors = androidx.compose.material3.RadioButtonDefaults.colors(
                    selectedColor = MaterialTheme.colorScheme.primary,
                    unselectedColor = MaterialTheme.colorScheme.outline,
                ),
            )
            Spacer(Modifier.width(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(description, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

/** Pill-shaped single-choice control (speed, camera angle, filters). Each option exposes its selected state. */
@Composable
fun SegmentedPill(
    options: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
    accent: Color = MaterialTheme.colorScheme.onSurface,
    compact: Boolean = false,
) {
    Surface(modifier = modifier, shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
        Row(Modifier.padding(4.dp)) {
            options.forEachIndexed { i, label ->
                val selected = i == selectedIndex
                Surface(
                    modifier = Modifier
                        .heightIn(min = if (compact) 40.dp else 44.dp)
                        .selectable(selected = selected, onClick = { onSelect(i) }, role = Role.RadioButton),
                    shape = RoundedCornerShape(50),
                    color = if (selected) accent else Color.Transparent,
                ) {
                    Box(Modifier.padding(horizontal = if (compact) 12.dp else 16.dp, vertical = if (compact) 7.dp else 10.dp), contentAlignment = Alignment.Center) {
                        Text(
                            label,
                            style = if (compact) MaterialTheme.typography.labelMedium else MaterialTheme.typography.labelLarge,
                            color = if (selected) MaterialTheme.colorScheme.background else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}

/** Small read-only fact, e.g. "60 s". */
@Composable
fun FactChip(text: String, modifier: Modifier = Modifier) {
    Surface(modifier = modifier, shape = RoundedCornerShape(50), color = Color.Transparent, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
        Text(text, Modifier.padding(horizontal = 12.dp, vertical = 6.dp), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

// ---------------------------------------------------------------------------------------------- actions

/** Full-width main action. */
@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    color: Color = MaterialTheme.colorScheme.primary,
) {
    androidx.compose.material3.Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().heightIn(min = 56.dp),
        shape = RoundedCornerShape(16.dp),
        colors = androidx.compose.material3.ButtonDefaults.buttonColors(
            containerColor = color,
            contentColor = MfColors.OnGold,
            disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
        ),
    ) { Text(text, style = MaterialTheme.typography.titleMedium.copy(fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)) }
}

/** Large round action with a text label underneath for clarity (workout controls). */
@Composable
fun RoundAction(
    symbol: String,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    container: Color = MaterialTheme.colorScheme.surface,
    content: Color = MaterialTheme.colorScheme.onSurface,
    size: Dp = 56.dp,
) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Surface(
            onClick = onClick,
            modifier = Modifier.width(size).height(size).semantics { contentDescription = label; role = Role.Button },
            shape = CircleShape,
            color = container,
            border = if (container == MaterialTheme.colorScheme.surface) BorderStroke(1.dp, MaterialTheme.colorScheme.outline) else null,
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(symbol, style = MaterialTheme.typography.titleLarge, color = content, modifier = Modifier.clearAndSetSemantics {})
            }
        }
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.clearAndSetSemantics {})
    }
}

// ---------------------------------------------------------------------------------------------- numbers

/** Big number with a caption. */
@Composable
fun StatTile(value: String, label: String, modifier: Modifier = Modifier, accent: Color = MaterialTheme.colorScheme.onSurface) {
    Surface(modifier = modifier, shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(value, style = MaterialTheme.typography.headlineLarge, color = accent)
            Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
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
    val track = MaterialTheme.colorScheme.outline
    val muted = MaterialTheme.colorScheme.onSurfaceVariant
    Box(modifier, contentAlignment = Alignment.Center) {
        Canvas(Modifier.matchParentSize()) {
            val stroke = size.minDimension * 0.055f
            val arcSize = Size(size.minDimension - stroke, size.minDimension - stroke)
            val topLeft = Offset((size.width - arcSize.width) / 2, (size.height - arcSize.height) / 2)
            val style = Stroke(stroke, cap = StrokeCap.Round)
            drawArc(track, -90f, 360f, false, topLeft, arcSize, style = style)
            drawArc(if (dimmed) muted else accent, -90f, 360f * fraction.coerceIn(0f, 1f), false, topLeft, arcSize, style = style)
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, style = MaterialTheme.typography.displaySmall, color = if (dimmed) muted else MaterialTheme.colorScheme.onSurface)
            if (caption != null) Text(caption, style = MaterialTheme.typography.labelMedium, color = muted)
        }
    }
}

// ---------------------------------------------------------------------------------------------- lesson cards

/**
 * Picture card for a lesson: the coach performing the move in front of the move's name on a tinted field, the
 * name and length below. The whole card is one button; the picture is decorative (the title says what it is).
 */
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
    Surface(
        onClick = onClick,
        modifier = modifier.semantics { role = Role.Button },
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column {
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(artHeight)
                    .background(stageBrush(accent)),
            ) {
                StageFloor(accent, Modifier.align(Alignment.BottomCenter))
                CoachArt(artPath, Modifier.fillMaxSize().padding(top = 12.dp, bottom = 2.dp))
                if (badge != null) {
                    Surface(
                        modifier = Modifier.align(Alignment.TopStart).padding(10.dp),
                        shape = RoundedCornerShape(50),
                        color = MaterialTheme.colorScheme.background.copy(alpha = 0.7f),
                        border = BorderStroke(1.dp, accent.copy(alpha = 0.5f)),
                    ) {
                        Text(badge.uppercase(), Modifier.padding(horizontal = 9.dp, vertical = 3.dp), style = MaterialTheme.typography.labelSmall, color = accent)
                    }
                }
            }
            Column(Modifier.padding(start = 14.dp, end = 14.dp, top = 12.dp, bottom = 14.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(meta, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
            }
        }
    }
}

/** A tinted stage with the exercise name behind whatever [content] draws (a coach still or the live 3D coach). */
@Composable
fun CoachStage(
    name: String,
    accent: Color,
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(
        modifier
            .clip(RoundedCornerShape(24.dp))
            .background(stageBrush(accent))
    ) {
        StageFloor(accent, Modifier.align(Alignment.BottomCenter))
        content()
    }
}

/** Spotlit stage: a soft pool of the accent colour from above, falling off into the graphite ground. */
@Composable
fun stageBrush(accent: Color): Brush = Brush.verticalGradient(
    0f to accent.copy(alpha = 0.16f),
    0.55f to MaterialTheme.colorScheme.surfaceVariant,
    1f to MaterialTheme.colorScheme.surface,
)

/** Soft elliptical floor shadow so the coach stands on something instead of floating. */
@Composable
fun StageFloor(accent: Color, modifier: Modifier = Modifier) {
    Box(
        modifier
            .padding(bottom = 18.dp)
            .fillMaxWidth(0.62f)
            .height(26.dp)
            .clip(androidx.compose.foundation.shape.GenericShape { size, _ -> addOval(androidx.compose.ui.geometry.Rect(0f, 0f, size.width, size.height)) })
            .background(Brush.radialGradient(listOf(Color.Black.copy(alpha = 0.55f), Color.Transparent))),
    )
}

fun formatClock(totalSeconds: Int): String {
    val s = totalSeconds.coerceAtLeast(0)
    return "%d:%02d".format(s / 60, s % 60)
}

/** "2 min" for ≥ 60 s, else "45 s". */
fun formatLength(seconds: Int): String = if (seconds >= 60) "${(seconds + 30) / 60} min" else "$seconds s"
