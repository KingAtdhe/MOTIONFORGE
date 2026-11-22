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
 * MOTIONFORGE identity v3 — "training campaign".
 *
 * The coach renders are the brand: they sit large on a photo-studio grey backdrop, and heavy, extra-wide Archivo
 * lettering is set over them like a sports poster. Everything around that stays quiet: true black and white, no card
 * outlines, no glows, sentence-case labels. Colour is information only — a small chalk-blue or glove-red marker says
 * which kind of lesson it is, and the workout timer uses the same hue. The primary action is a white pill.
 * v1 colour names are kept so every screen picks up the palette.
 */
object MfColors {
    val Ground = Color(0xFF000000)          // the page
    val Paper = Color(0xFF171716)           // quiet blocks (notes, settings groups)
    val Raised = Color(0xFF232321)          // pressed / nested
    val Rule = Color(0xFF2E2E2C)            // dividers, only where rows need separating
    val Ink = Color(0xFFFFFFFF)
    val Slate = Color(0xFF8F8F8A)           // secondary text

    // the studio backdrop behind every coach render (a seamless paper sweep: lighter at the top, darker at the floor)
    val StudioTop = Color(0xFF3A3A37)
    val StudioFloor = Color(0xFF1C1C1B)

    // information colours
    val Chalk = Color(0xFF9CC4FF)           // fitness
    val GloveRed = Color(0xFFFF5A4E)        // fighting fundamentals
    val Cobalt = Chalk                      // v1 names
    val Glove = GloveRed
    val Gold = Chalk                        // v2 name (now: fitness marker)
    val OnGold = Color(0xFF000000)          // text on a filled accent or white button

    val Signal = Color(0xFF6CD49B)
    val Caution = Color(0xFFF2C14E)
    val Halt = Color(0xFFFF6159)

    // the workout screen uses the same ground
    val Night = Ground
    val NightRaised = Paper
    val NightRule = Rule
    val OnNight = Ink
    val OnNightMuted = Slate
    val CautionOnNight = Caution
    val SignalOnNight = Signal
}

/** Category colour (always paired with a text label). */
val TrainingCategory.accent: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> MfColors.Chalk
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.GloveRed
    }

val TrainingCategory.accentOnNight: Color
    get() = accent

/** Archivo (variable, OFL): one family; width and weight carry the hierarchy. */
@OptIn(ExperimentalTextApi::class)
private fun archivo(weight: Int, width: Float) = Font(
    R.font.archivo,
    weight = FontWeight(weight),
    style = FontStyle.Normal,
    variationSettings = FontVariation.Settings(FontVariation.weight(weight), FontVariation.width(width)),
)

/** Extra-wide, heavy: headlines and big numbers, the "poster" voice. */
val DisplayFont = FontFamily(archivo(700, 125f), archivo(800, 125f), archivo(900, 125f))
/** Semi-wide: card and section titles. */
val TitleFont = FontFamily(archivo(600, 110f), archivo(700, 110f))
/** Normal width: everything you read. */
val BodyFont = FontFamily(archivo(400, 100f), archivo(500, 100f), archivo(600, 100f), archivo(700, 100f))

private val scheme = darkColorScheme(
    primary = MfColors.Ink,
    onPrimary = Color.Black,
    primaryContainer = MfColors.Raised,
    onPrimaryContainer = MfColors.Ink,
    secondary = MfColors.GloveRed,
    onSecondary = Color.Black,
    background = MfColors.Ground,
    onBackground = MfColors.Ink,
    surface = MfColors.Paper,
    onSurface = MfColors.Ink,
    surfaceVariant = MfColors.Raised,
    onSurfaceVariant = MfColors.Slate,
    surfaceContainer = MfColors.Paper,
    surfaceContainerHigh = MfColors.Raised,
    outline = MfColors.Rule,
    outlineVariant = MfColors.Rule,
    error = MfColors.Halt,
    onError = Color.Black,
)

private val typography = Typography(
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Black, fontSize = 64.sp, lineHeight = 60.sp, letterSpacing = (-0.02).em),
    displayMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Black, fontSize = 48.sp, lineHeight = 46.sp, letterSpacing = (-0.02).em),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 34.sp, lineHeight = 34.sp, letterSpacing = (-0.015).em),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 30.sp, lineHeight = 31.sp, letterSpacing = (-0.015).em),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 25.sp, lineHeight = 27.sp, letterSpacing = (-0.01).em),
    headlineSmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 19.sp, lineHeight = 22.sp, letterSpacing = (-0.005).em),
    titleLarge = TextStyle(fontFamily = TitleFont, fontWeight = FontWeight.Bold, fontSize = 17.sp, lineHeight = 21.sp),
    titleMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp),
    titleSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 17.sp),
    labelLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 18.sp),
    labelMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 17.sp),
    labelSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, lineHeight = 16.sp),
)

// radii follow hierarchy: pictures are nearly square-cut, blocks softer, buttons are pills
private val shapes = Shapes(
    extraSmall = RoundedCornerShape(2.dp),
    small = RoundedCornerShape(4.dp),
    medium = RoundedCornerShape(10.dp),
    large = RoundedCornerShape(14.dp),
)

/** [night] kept for callers; the whole app now runs on the same black ground. */
@Composable
fun MotionForgeTheme(night: Boolean = false, content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = typography, shapes = shapes) {
        // text outside a Surface (onboarding, page headings) defaults to white, not the platform's black
        androidx.compose.runtime.CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides scheme.onBackground, content = content)
    }
}
