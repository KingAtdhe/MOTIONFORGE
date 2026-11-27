package eu.motionforge.app.core.design

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import eu.motionforge.app.core.i18n.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.time.DayOfWeek
import java.time.format.TextStyle
import java.util.Locale

/**
 * Mon–Sun as ticks on the measuring scale: a tall ink tick on days you trained, a short one otherwise, today's label in
 * bold. Each day is labelled, so it's never colour-only.
 */
@Composable
fun WeekTicks(trained: Set<DayOfWeek>, today: DayOfWeek, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().height(40.dp), verticalAlignment = Alignment.Bottom) {
            DayOfWeek.entries.forEach { d ->
                val done = d in trained
                val name = d.getDisplayName(TextStyle.FULL, Locale.getDefault())
                Box(
                    Modifier.weight(1f).semantics { contentDescription = "$name: " + if (done) "trained" else "no session" },
                    contentAlignment = Alignment.BottomCenter,
                ) {
                    Box(
                        Modifier
                            .width(if (done) 6.dp else 2.dp)
                            .height(if (done) 36.dp else 12.dp)
                            .background(if (done) MfColors.Ink else MaterialTheme.colorScheme.onSurfaceVariant),
                    )
                }
            }
        }
        Box(Modifier.fillMaxWidth().height(1.dp).background(MaterialTheme.colorScheme.onSurfaceVariant))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            DayOfWeek.entries.forEach { d ->
                Text(
                    d.getDisplayName(TextStyle.SHORT, Locale.getDefault()).take(2),
                    modifier = Modifier.weight(1f),
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = if (d == today) FontWeight.Bold else FontWeight.Medium),
                    color = if (d == today) MaterialTheme.colorScheme.onBackground else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
