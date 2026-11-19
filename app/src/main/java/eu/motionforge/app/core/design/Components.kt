package eu.motionforge.app.core.design

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.ui.graphics.Brush
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.pose.TrackingState

/** Flat panel used for content blocks. Clickable only when [onClick] is given. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(14.dp)
    val border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
    val inner: @Composable () -> Unit = {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp), content = content)
    }
    if (onClick != null) {
        Surface(
            onClick = onClick,
            modifier = modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { role = Role.Button },
            shape = shape,
            color = MaterialTheme.colorScheme.surface,
            border = border,
            content = inner,
        )
    } else {
        Surface(modifier = modifier.fillMaxWidth(), shape = shape, color = MaterialTheme.colorScheme.surface, border = border, content = inner)
    }
}

/** Small monospace section label, e.g. "SAFETY". */
@Composable
fun Eyebrow(text: String, color: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = color)
}

/**
 * Tracking status chip. Uses a text label and a shape marker as well as colour,
 * so status is never conveyed by colour alone.
 */
@Composable
fun TrackingStatusChip(state: TrackingState, modifier: Modifier = Modifier) {
    val (color, marker) = when (state) {
        TrackingState.TRACKING -> MfColors.Signal to "●"
        TrackingState.CALIBRATING, TrackingState.CAMERA_INITIALIZING, TrackingState.PAUSED -> MfColors.Muted to "◐"
        TrackingState.CAMERA_ERROR, TrackingState.CAMERA_PERMISSION_DENIED -> MfColors.Halt to "■"
        else -> MfColors.Caution to "▲"
    }
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(50),
        color = MfColors.Ink.copy(alpha = 0.82f),
        border = BorderStroke(1.dp, color),
    ) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(marker, color = color, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(8.dp))
            Text(state.userMessage, color = MfColors.Chalk, style = MaterialTheme.typography.labelLarge)
        }
    }
}

/**
 * A two-state choice button (filters, segment pickers). Exposes its selected state to
 * accessibility services instead of relying on colour alone.
 */
@Composable
fun ChoiceButton(label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val semanticsModifier = modifier.semantics { this.selected = selected }
    if (selected) {
        androidx.compose.material3.Button(onClick = onClick, modifier = semanticsModifier) { Text("✓ $label") }
    } else {
        androidx.compose.material3.OutlinedButton(onClick = onClick, modifier = semanticsModifier) { Text(label) }
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
        shape = RoundedCornerShape(14.dp),
        color = if (selected) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface,
        border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline),
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.material3.RadioButton(selected = selected, onClick = null)
            Spacer(Modifier.width(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(description, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

/** Small read-only fact chip, e.g. "60 s". */
@Composable
fun FactChip(text: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
    ) {
        Text(text, Modifier.padding(horizontal = 10.dp, vertical = 5.dp), style = MaterialTheme.typography.labelMedium)
    }
}

/** Full-width main action. */
@Composable
fun PrimaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    androidx.compose.material3.Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().heightIn(min = 56.dp),
        shape = RoundedCornerShape(16.dp),
    ) { Text(text.uppercase(), style = MaterialTheme.typography.titleLarge) }
}

/** Large call-to-action card with an accent gradient. */
@Composable
fun HeroCard(
    eyebrow: String,
    title: String,
    body: String,
    action: String,
    accent: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(22.dp)
    Surface(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().semantics { role = Role.Button },
        shape = shape,
        color = Color.Transparent,
        border = BorderStroke(1.dp, accent.copy(alpha = 0.55f)),
    ) {
        Column(
            Modifier
                .background(Brush.linearGradient(listOf(accent.copy(alpha = 0.30f), MfColors.Panel, MfColors.Panel)))
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Eyebrow(eyebrow, color = accent)
            Text(title.uppercase(), style = MaterialTheme.typography.headlineLarge)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.width(1.dp))
            Surface(shape = RoundedCornerShape(14.dp), color = accent) {
                Text(
                    "▶  ${action.uppercase()}",
                    Modifier.padding(horizontal = 18.dp, vertical = 12.dp),
                    style = MaterialTheme.typography.titleLarge,
                    color = MfColors.Ink,
                )
            }
        }
    }
}

/** Big number with a caption. */
@Composable
fun StatTile(value: String, label: String, modifier: Modifier = Modifier, accent: Color = MfColors.Chalk) {
    Surface(modifier = modifier, shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
            Text(value, style = MaterialTheme.typography.displaySmall, color = accent)
            Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/** Lesson list card with a category accent bar. */
@Composable
fun LessonCard(
    title: String,
    subtitle: String,
    facts: List<String>,
    accent: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    eyebrow: String? = null,
) {
    Surface(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().semantics { role = Role.Button },
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Row(Modifier.height(IntrinsicSize.Min)) {
            Box(Modifier.width(5.dp).fillMaxHeight().background(accent))
            Column(Modifier.padding(16.dp).weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (eyebrow != null) Eyebrow(eyebrow, color = accent)
                Text(title.uppercase(), style = MaterialTheme.typography.titleLarge)
                Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { facts.forEach { FactChip(it) } }
            }
            Text("›", Modifier.align(Alignment.CenterVertically).padding(end = 16.dp), style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

fun formatClock(totalSeconds: Int): String {
    val s = totalSeconds.coerceAtLeast(0)
    return "%d:%02d".format(s / 60, s % 60)
}

/**
 * Picture card for a lesson: the coach performing the move over a category-tinted backdrop, name and facts below.
 * The whole card is one button; the picture is decorative (the title says what it is).
 */
@Composable
fun LessonTile(
    title: String,
    meta: String,
    accent: Color,
    artPath: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    eyebrow: String? = null,
    artHeight: androidx.compose.ui.unit.Dp = 168.dp,
) {
    Surface(
        onClick = onClick,
        modifier = modifier.semantics { role = Role.Button },
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Column {
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(artHeight)
                    .background(Brush.verticalGradient(listOf(accent.copy(alpha = 0.05f), accent.copy(alpha = 0.30f)))),
            ) {
                CoachArt(
                    artPath,
                    Modifier.fillMaxWidth().height(artHeight).padding(top = 8.dp),
                )
                if (eyebrow != null) {
                    Surface(
                        modifier = Modifier.padding(10.dp),
                        shape = RoundedCornerShape(50),
                        color = MfColors.Ink.copy(alpha = 0.78f),
                    ) {
                        Text(
                            eyebrow.uppercase(),
                            Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = accent,
                        )
                    }
                }
            }
            Box(Modifier.fillMaxWidth().height(3.dp).background(accent))
            Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title.uppercase(), style = MaterialTheme.typography.titleLarge, maxLines = 2)
                Text(meta, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
            }
        }
    }
}

/** Pill-shaped single-choice control (speed, camera angle). Each option exposes its selected state. */
@Composable
fun SegmentedPill(
    options: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
    accent: Color = MfColors.Volt,
) {
    Surface(modifier = modifier, shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
        Row(Modifier.padding(4.dp)) {
            options.forEachIndexed { i, label ->
                val selected = i == selectedIndex
                Surface(
                    modifier = Modifier
                        .heightIn(min = 44.dp)
                        .selectable(selected = selected, onClick = { onSelect(i) }, role = Role.RadioButton),
                    shape = RoundedCornerShape(50),
                    color = if (selected) accent else Color.Transparent,
                ) {
                    Box(Modifier.padding(horizontal = 16.dp, vertical = 10.dp), contentAlignment = Alignment.Center) {
                        Text(label, style = MaterialTheme.typography.labelLarge, color = if (selected) MfColors.Ink else MfColors.Chalk)
                    }
                }
            }
        }
    }
}

/** Section heading with an optional trailing count, used between home/train blocks. */
@Composable
fun SectionHeader(title: String, trailing: String? = null) {
    Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.Bottom) {
        Text(
            title.uppercase(),
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.weight(1f).semantics { androidx.compose.ui.semantics.heading() },
        )
        if (trailing != null) Text(trailing.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
