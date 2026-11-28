package eu.motionforge.app.feature.progress

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.core.design.MfColors
import eu.motionforge.app.core.design.MfType
import eu.motionforge.app.core.design.Panel
import eu.motionforge.app.core.design.SectionHeader
import eu.motionforge.app.core.design.ThinRule
import eu.motionforge.app.core.i18n.Text
import eu.motionforge.app.core.i18n.tr

/** On the session summary: the share of reps with nothing flagged, with what it does and does not mean. */
@Composable
fun FormCheckPanel(t: FormTally) {
    Panel {
        Row(verticalAlignment = Alignment.Top, modifier = Modifier.semantics(mergeDescendants = true) {}) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("Form check", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("${t.clean} of ${t.attempts} reps with nothing flagged", style = MaterialTheme.typography.titleMedium)
            }
            Text("${t.percent}%", style = MfType.Numeral)
        }
        Text(
            "Counted on squats, push-ups and lunges only. The camera checks a few simple rules on each rep; it does not judge your technique beyond them.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/** On the You page: the form score per exercise over the last sets (bars), the latest in ink. */
@Composable
fun FormTrendsSection(trends: List<FormTrend>) {
    if (trends.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        SectionHeader("Form", trailing = "reps with nothing flagged")
        trends.forEachIndexed { i, t ->
            if (i > 0) ThinRule()
            val description = tr(t.name) + ". " + tr("Latest ${t.last}%") + "."
            Row(
                Modifier.fillMaxWidth().padding(vertical = 10.dp).clearAndSetSemantics { contentDescription = description },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(t.name, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Row(Modifier.height(36.dp), horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.Bottom) {
                    t.recent.forEachIndexed { j, p ->
                        Box(
                            Modifier.width(14.dp).height((4 + 32 * p / 100).dp)
                                .background(if (j == t.recent.lastIndex) MfColors.Ink else MfColors.Rule),
                        )
                    }
                }
                Text("${t.last}%", style = MfType.NumeralSmall, modifier = Modifier.padding(start = 12.dp))
            }
        }
    }
}
