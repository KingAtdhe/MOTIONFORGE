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
 * MOTIONFORGE identity v4 — "gym floor".
 *
 * A light, concrete-grey page with black type, like a printed training programme pinned up in a gym. The coach always
 * stands in a flat field of colour — electric cobalt for fitness, blaze orange for fighting — so a lesson's kind is
 * the size of the picture, not a dot. Big numbers (minutes, reps, the timer) use Archivo at its narrowest width, titles
 * at its widest. Buttons are square-cut black bars. The workout screen stays dark for the camera.
 * Older colour names are kept so every screen picks up the palette.
 */
object MfColors {
    val Ground = Color(0xFFE3E3DE)          // the page: concrete grey
    val Paper = Color(0xFFF1F1EE)           // quiet blocks
    val Raised = Color(0xFFD3D3CD)          // pressed / tracks
    val Rule = Color(0xFFBDBDB6)            // hairlines
    val Ink = Color(0xFF000000)
    val Slate = Color(0xFF5E5E59)           // secondary text (7:1 on the page)

    // the two fields the coach stands in
    val Cobalt = Color(0xFF2B3BFF)          // fitness
    val Blaze = Color(0xFFFF5A1F)           // fighting fundamentals
    val OnCobalt = Color(0xFFFFFFFF)
    val OnBlaze = Color(0xFF000000)
    val Chalk = Cobalt                      // older names
    val GloveRed = Blaze
    val Glove = Blaze
    val Gold = Cobalt
    val OnGold = Color(0xFFFFFFFF)          // text on a filled accent or black button
    val StudioTop = Cobalt
    val StudioFloor = Cobalt

    val Signal = Color(0xFF0B7A43)
    val Caution = Color(0xFF8A5A00)
    val Halt = Color(0xFFC8261B)

    // the workout screen: black, for the camera picture
    val Night = Color(0xFF000000)
    val NightRaised = Color(0xFF1A1A19)
    val NightRule = Color(0xFF2E2E2C)
    val OnNight = Color(0xFFFFFFFF)
    val OnNightMuted = Color(0xFF9A9A94)
    val CautionOnNight = Color(0xFFF2C14E)
    val SignalOnNight = Color(0xFF6CD49B)
}

/** Category colour (always paired with a text label). */
val TrainingCategory.accent: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> MfColors.Cobalt
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.Blaze
    }

/** Text colour that reads on [accent] used as a field. */
val TrainingCategory.onAccent: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> MfColors.OnCobalt
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.OnBlaze
    }

/** On the black workout screen. */
val TrainingCategory.accentOnNight: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> Color(0xFF8A96FF)
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.Blaze
    }

/** Text colour for a field of [c] (one of the two category colours). */
fun onField(c: Color): Color = if (c == MfColors.Blaze) MfColors.OnBlaze else Color.White

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
/** Narrowest, heaviest: big numbers only (minutes, reps, the timer). */
val NumeralFont = FontFamily(archivo(800, 62f), archivo(900, 62f))
/** Normal width: everything you read. */
val BodyFont = FontFamily(archivo(400, 100f), archivo(500, 100f), archivo(600, 100f), archivo(700, 100f))

private val scheme = androidx.compose.material3.lightColorScheme(
    primary = MfColors.Ink,
    onPrimary = Color.White,
    primaryContainer = MfColors.Raised,
    onPrimaryContainer = MfColors.Ink,
    secondary = MfColors.Blaze,
    onSecondary = Color.Black,
    background = MfColors.Ground,
    onBackground = MfColors.Ink,
    surface = MfColors.Ground,
    onSurface = MfColors.Ink,
    surfaceVariant = MfColors.Raised,
    onSurfaceVariant = MfColors.Slate,
    surfaceContainer = MfColors.Paper,
    surfaceContainerHigh = MfColors.Paper,
    surfaceContainerLow = MfColors.Paper,
    outline = MfColors.Rule,
    outlineVariant = MfColors.Rule,
    error = MfColors.Halt,
    onError = Color.White,
)

private val nightScheme = darkColorScheme(
    primary = Color.White,
    onPrimary = Color.Black,
    primaryContainer = MfColors.NightRaised,
    onPrimaryContainer = Color.White,
    secondary = MfColors.Blaze,
    onSecondary = Color.Black,
    background = MfColors.Night,
    onBackground = MfColors.OnNight,
    surface = MfColors.NightRaised,
    onSurface = MfColors.OnNight,
    surfaceVariant = Color(0xFF262624),
    onSurfaceVariant = MfColors.OnNightMuted,
    surfaceContainer = MfColors.NightRaised,
    surfaceContainerHigh = Color(0xFF262624),
    outline = MfColors.NightRule,
    outlineVariant = MfColors.NightRule,
    error = Color(0xFFFF6159),
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
    small = RoundedCornerShape(2.dp),
    medium = RoundedCornerShape(3.dp),
    large = RoundedCornerShape(4.dp),
)

/** Big narrow numbers. */
object MfType {
    val Numeral = TextStyle(fontFamily = NumeralFont, fontWeight = FontWeight.Black, fontSize = 64.sp, lineHeight = 60.sp, letterSpacing = (-0.01).em)
    val NumeralHuge = TextStyle(fontFamily = NumeralFont, fontWeight = FontWeight.Black, fontSize = 148.sp, lineHeight = 132.sp, letterSpacing = (-0.02).em)
    val NumeralSmall = TextStyle(fontFamily = NumeralFont, fontWeight = FontWeight.ExtraBold, fontSize = 30.sp, lineHeight = 30.sp)
}

/** Light "gym floor" theme; [night] = the black workout screen. */
@Composable
fun MotionForgeTheme(night: Boolean = false, content: @Composable () -> Unit) {
    val cs = if (night) nightScheme else scheme
    MaterialTheme(colorScheme = cs, typography = typography, shapes = shapes) {
        androidx.compose.runtime.CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides cs.onBackground, content = content)
    }
}
