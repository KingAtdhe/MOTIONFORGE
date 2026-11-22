package eu.motionforge.app.core.design

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import eu.motionforge.app.R
import eu.motionforge.app.core.model.TrainingCategory

/**
 * MOTIONFORGE identity (v2, "premium"): a warm near-black ground, graphite surfaces separated by fine hairlines, warm
 * off-white type, and one signature colour — champagne gold — used sparingly for the primary action and for fitness.
 * Fighting fundamentals use a deep copper. Colour is always paired with text, never the only signal.
 * The names below are kept from v1 so every screen picks up the new palette.
 */
object MfColors {
    // grounds and surfaces
    val Ground = Color(0xFF0B0B0D)          // app background
    val Paper = Color(0xFF151518)           // cards / panels
    val Raised = Color(0xFF1D1D21)          // pressed / nested surfaces
    val Rule = Color(0xFF2A2A30)            // hairlines
    val Ink = Color(0xFFF3F1EC)             // primary text (warm white)
    val Slate = Color(0xFF9D9BA3)           // secondary text

    // signature and category colours
    val Gold = Color(0xFFD7B474)
    val GoldDeep = Color(0xFFB08A4A)
    val Copper = Color(0xFFD0714A)
    val Cobalt = Gold                       // v1 name for the fitness / primary colour
    val Glove = Copper                      // v1 name for the fighting colour
    val OnGold = Color(0xFF16130E)

    // status colours, readable as text on the dark ground
    val Signal = Color(0xFF7DD3A8)
    val Caution = Color(0xFFE6BC5C)
    val Halt = Color(0xFFEF7468)

    // the workout screen: a touch darker so the camera and coach carry the screen
    val Night = Color(0xFF070708)
    val NightRaised = Color(0xFF17171A)
    val NightRule = Color(0xFF2A2A30)
    val OnNight = Ink
    val OnNightMuted = Slate
    val CautionOnNight = Caution
    val SignalOnNight = Signal
}

/** Category colour (always paired with a text label). */
val TrainingCategory.accent: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> MfColors.Gold
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.Copper
    }

/** Category colour on the workout scheme (same hues; the grounds are equally dark). */
val TrainingCategory.accentOnNight: Color
    get() = accent

/** Manrope (variable font, OFL): one geometric family for everything, weight carries the hierarchy. */
@OptIn(ExperimentalTextApi::class)
private fun manrope(weight: Int) = Font(
    R.font.manrope,
    weight = FontWeight(weight),
    style = FontStyle.Normal,
    variationSettings = FontVariation.Settings(FontVariation.weight(weight)),
)

val BodyFont = FontFamily(manrope(400), manrope(500), manrope(600), manrope(700), manrope(800))
val DisplayFont = BodyFont

private val scheme = darkColorScheme(
    primary = MfColors.Gold,
    onPrimary = MfColors.OnGold,
    primaryContainer = Color(0xFF2A2418),
    onPrimaryContainer = MfColors.Gold,
    secondary = MfColors.Copper,
    onSecondary = MfColors.OnGold,
    secondaryContainer = Color(0xFF2A1C16),
    onSecondaryContainer = MfColors.Copper,
    background = MfColors.Ground,
    onBackground = MfColors.Ink,
    surface = MfColors.Paper,
    onSurface = MfColors.Ink,
    surfaceVariant = MfColors.Raised,
    onSurfaceVariant = MfColors.Slate,
    surfaceContainer = MfColors.Paper,
    surfaceContainerHigh = MfColors.Raised,
    outline = MfColors.Rule,
    outlineVariant = Color(0xFF222227),
    error = MfColors.Halt,
    onError = MfColors.OnGold,
)

private val nightScheme = scheme.copy(
    background = MfColors.Night,
    surface = MfColors.NightRaised,
    surfaceVariant = MfColors.NightRaised,
    outline = MfColors.NightRule,
)

private val typography = Typography(
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 72.sp, lineHeight = 74.sp, letterSpacing = (-0.03).em),
    displayMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 52.sp, lineHeight = 56.sp, letterSpacing = (-0.03).em),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 36.sp, lineHeight = 40.sp, letterSpacing = (-0.02).em),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 30.sp, lineHeight = 36.sp, letterSpacing = (-0.02).em),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 26.sp, lineHeight = 32.sp, letterSpacing = (-0.015).em),
    headlineSmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 21.sp, lineHeight = 27.sp, letterSpacing = (-0.01).em),
    titleLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 18.sp, lineHeight = 24.sp, letterSpacing = (-0.005).em),
    titleMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp),
    titleSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 25.sp),
    bodyMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 17.sp),
    labelLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 18.sp, letterSpacing = 0.01.em),
    labelMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.01.em),
    labelSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 11.sp, lineHeight = 14.sp, letterSpacing = 0.14.em),
)

private val shapes = Shapes(
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(24.dp),
)

/** [night] = the workout scheme (running session, camera): the same identity on an even darker ground. */
@Composable
fun MotionForgeTheme(night: Boolean = false, content: @Composable () -> Unit) {
    val colors = if (night) nightScheme else scheme
    MaterialTheme(colorScheme = colors, typography = typography, shapes = shapes) {
        // text outside a Surface (onboarding, page headings) must default to the light ink, not the platform's black
        androidx.compose.runtime.CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides colors.onBackground, content = content)
    }
}
