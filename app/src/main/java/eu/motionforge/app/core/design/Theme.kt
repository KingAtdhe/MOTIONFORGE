package eu.motionforge.app.core.design

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

object MfColors {
    val Ink = Color(0xFF0E1114)
    val Panel = Color(0xFF161B20)
    val PanelRaised = Color(0xFF1E252C)
    val Line = Color(0xFF2B343D)
    val Chalk = Color(0xFFE8ECEF)
    val Muted = Color(0xFF9AA6B0)
    val Signal = Color(0xFF6EE7B7) // tracking OK
    val Caution = Color(0xFFF2B544) // needs adjustment
    val Halt = Color(0xFFF07167) // error / stop
}

private val scheme = darkColorScheme(
    primary = MfColors.Signal,
    onPrimary = MfColors.Ink,
    secondary = MfColors.Caution,
    onSecondary = MfColors.Ink,
    background = MfColors.Ink,
    onBackground = MfColors.Chalk,
    surface = MfColors.Panel,
    onSurface = MfColors.Chalk,
    surfaceVariant = MfColors.PanelRaised,
    onSurfaceVariant = MfColors.Muted,
    outline = MfColors.Line,
    error = MfColors.Halt,
    onError = MfColors.Ink,
)

private val typography = Typography(
    headlineMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 26.sp, letterSpacing = (-0.3).sp),
    titleLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.SemiBold, fontSize = 20.sp),
    titleMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.SemiBold, fontSize = 16.sp),
    bodyLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, letterSpacing = 0.4.sp),
    labelSmall = TextStyle(fontFamily = FontFamily.Monospace, fontSize = 11.sp, letterSpacing = 0.6.sp),
)

@Composable
fun MotionForgeTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = typography, content = content)
}
