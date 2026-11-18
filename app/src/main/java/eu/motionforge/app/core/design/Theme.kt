package eu.motionforge.app.core.design

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import eu.motionforge.app.R
import eu.motionforge.app.core.model.TrainingCategory

object MfColors {
    val Ink = Color(0xFF0B0D10)
    val Panel = Color(0xFF14181D)
    val PanelRaised = Color(0xFF1D232A)
    val Line = Color(0xFF2A323B)
    val Chalk = Color(0xFFF2F4F5)
    val Muted = Color(0xFF97A3AE)
    val Volt = Color(0xFFC8F542) // brand / fitness
    val Ember = Color(0xFFFF7A45) // fighting fundamentals
    val Signal = Color(0xFF5EEAD4) // tracking OK
    val Caution = Color(0xFFF2B544) // needs adjustment
    val Halt = Color(0xFFF07167) // error / stop
}

/** Accent colour per training category (always paired with a text label, never colour alone). */
val TrainingCategory.accent: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> MfColors.Volt
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.Ember
    }

/** Barlow Condensed for headings and numbers, Barlow for reading text (SIL OFL, bundled). */
val DisplayFont = FontFamily(
    Font(R.font.barlow_condensed_semibold, FontWeight.SemiBold),
    Font(R.font.barlow_condensed_bold, FontWeight.Bold),
)
val BodyFont = FontFamily(
    Font(R.font.barlow_regular, FontWeight.Normal),
    Font(R.font.barlow_medium, FontWeight.Medium),
    Font(R.font.barlow_semibold, FontWeight.SemiBold),
)

private val scheme = darkColorScheme(
    primary = MfColors.Volt,
    onPrimary = MfColors.Ink,
    secondary = MfColors.Ember,
    onSecondary = MfColors.Ink,
    background = MfColors.Ink,
    onBackground = MfColors.Chalk,
    surface = MfColors.Panel,
    onSurface = MfColors.Chalk,
    surfaceVariant = MfColors.PanelRaised,
    onSurfaceVariant = MfColors.Muted,
    secondaryContainer = MfColors.PanelRaised,
    onSecondaryContainer = MfColors.Volt,
    outline = MfColors.Line,
    error = MfColors.Halt,
    onError = MfColors.Ink,
)

private val typography = Typography(
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 104.sp, lineHeight = 100.sp, letterSpacing = (-1).sp),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 44.sp, lineHeight = 44.sp),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 40.sp, lineHeight = 40.sp),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 34.sp),
    titleLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.SemiBold, fontSize = 25.sp, lineHeight = 28.sp),
    titleMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 17.sp, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontFamily = BodyFont, fontSize = 17.sp, lineHeight = 25.sp),
    bodyMedium = TextStyle(fontFamily = BodyFont, fontSize = 15.sp, lineHeight = 21.sp),
    labelLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 15.sp, letterSpacing = 0.3.sp),
    labelMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 13.sp),
    labelSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, letterSpacing = 1.4.sp),
)

private val shapes = Shapes(
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(22.dp),
)

@Composable
fun MotionForgeTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = typography, shapes = shapes, content = content)
}
