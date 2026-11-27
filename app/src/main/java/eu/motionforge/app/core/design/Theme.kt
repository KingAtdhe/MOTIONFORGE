package eu.motionforge.app.core.design

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import eu.motionforge.app.R
import eu.motionforge.app.core.model.TrainingCategory

/**
 * CORZA identity v5 — "motion lab" (docs: CORZA design plan, approved 2026-11-22).
 *
 * The app reads like a training lab's notebook: light silver pages with black photographic plates set into them. Every
 * lesson is shown as a motion study — several exposures of the coach on one plate, after Marey's chronophotographs —
 * and one timing-board yellow marks anything live or tappable. The workout screen is the full black plate, read from
 * the floor 2 m away. Type is Barlow, drawn from road signs, so numbers hold up at a distance.
 * Older colour names are kept as aliases so every screen picks up the palette.
 */
object MfColors {
    val Plate = Color(0xFF000000)           // motion studies, the 3D stage, the workout
    val Silver = Color(0xFFE8E8E4)          // the page
    val Sheet = Color(0xFFF4F4F1)           // quiet blocks on the page
    val Ink = Color(0xFF0D0D0D)
    val Graphite = Color(0xFF66665F)        // secondary text, 7:1 on silver
    val Rule = Color(0xFFCFCFC9)
    val Yellow = Color(0xFFFFD60A)          // timing-board yellow: the one action, live numbers. Always black text on it.
    val Cue = Color(0xFFFF6A3D)             // a correction during the workout, on the plate only, always with words

    // older names
    val Ground = Silver
    val Paper = Sheet
    val Raised = Color(0xFFDADAD5)
    val Slate = Graphite
    val Cobalt = Plate
    val Blaze = Plate
    val OnCobalt = Color.White
    val OnBlaze = Color.White
    val Chalk = Plate
    val GloveRed = Plate
    val Glove = Plate
    val Gold = Yellow
    val OnGold = Color(0xFF000000)
    val StudioTop = Plate
    val StudioFloor = Plate

    val Signal = Color(0xFF0B7A43)
    val Caution = Color(0xFF7A5200)
    val Halt = Color(0xFFC8261B)

    // the workout screen
    val Night = Plate
    val NightRaised = Color(0xFF161615)
    val NightRule = Color(0xFF2E2E2C)
    val OnNight = Color(0xFFFFFFFF)
    val OnNightMuted = Color(0xFFA3A39C)
    val CautionOnNight = Cue
    val SignalOnNight = Color(0xFF7BE0A8)
}

/** Lessons are told apart by words and by their motion study, not by colour: both kinds sit on the black plate. */
val TrainingCategory.accent: Color get() = MfColors.Plate

/** Text on a plate. */
val TrainingCategory.onAccent: Color get() = Color.White

/** Live numbers on the workout plate. */
val TrainingCategory.accentOnNight: Color get() = MfColors.Yellow

/** Text colour for a field of [c]. */
fun onField(c: Color): Color = if (c == MfColors.Yellow) Color.Black else Color.White

/** Barlow: everything you read. */
val BodyFont = FontFamily(
    Font(R.font.barlow_regular, FontWeight.Normal),
    Font(R.font.barlow_medium, FontWeight.Medium),
    Font(R.font.barlow_semibold, FontWeight.SemiBold),
    Font(R.font.barlow_bold, FontWeight.Bold),
)
/** Barlow Semi Condensed: screen titles and section heads. */
val DisplayFont = FontFamily(
    Font(R.font.barlow_semicond_semibold, FontWeight.SemiBold),
    Font(R.font.barlow_semicond_bold, FontWeight.Bold),
)
val TitleFont = BodyFont
/** Barlow Condensed: numbers you read from a distance (reps, time). */
val NumeralFont = FontFamily(
    Font(R.font.barlow_cond_semibold, FontWeight.SemiBold),
    Font(R.font.barlow_cond_bold, FontWeight.Bold),
    Font(R.font.barlow_cond_extrabold, FontWeight.ExtraBold),
)

private val scheme = lightColorScheme(
    primary = MfColors.Ink,
    onPrimary = Color.White,
    primaryContainer = MfColors.Raised,
    onPrimaryContainer = MfColors.Ink,
    secondary = MfColors.Yellow,
    onSecondary = Color.Black,
    background = MfColors.Silver,
    onBackground = MfColors.Ink,
    surface = MfColors.Silver,
    onSurface = MfColors.Ink,
    surfaceVariant = MfColors.Raised,
    onSurfaceVariant = MfColors.Graphite,
    surfaceContainer = MfColors.Sheet,
    surfaceContainerLow = MfColors.Sheet,
    surfaceContainerHigh = MfColors.Sheet,
    surfaceContainerHighest = MfColors.Raised,
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
    secondary = MfColors.Yellow,
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
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 48.sp, lineHeight = 50.sp, letterSpacing = (-0.01).em),
    displayMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 40.sp, lineHeight = 42.sp, letterSpacing = (-0.01).em),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 34.sp, lineHeight = 37.sp),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 30.sp, lineHeight = 33.sp),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 24.sp, lineHeight = 28.sp),
    headlineSmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 24.sp),
    titleLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 23.sp),
    titleMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp),
    titleSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Normal, fontSize = 13.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 18.sp),
    labelMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 17.sp),
    labelSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp),
)

private val shapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(6.dp),
    medium = RoundedCornerShape(6.dp),
    large = RoundedCornerShape(10.dp),
)

/** Big numbers in Barlow Condensed with tabular figures, so a ticking timer never jumps. */
object MfType {
    val Numeral = TextStyle(fontFamily = NumeralFont, fontWeight = FontWeight.ExtraBold, fontSize = 56.sp, lineHeight = 56.sp, fontFeatureSettings = "tnum")
    /** About 20 mm tall on a typical phone: readable from 2 m (10 mm per metre). */
    val NumeralHuge = TextStyle(fontFamily = NumeralFont, fontWeight = FontWeight.ExtraBold, fontSize = 120.sp, lineHeight = 112.sp, fontFeatureSettings = "tnum")
    val NumeralSmall = TextStyle(fontFamily = NumeralFont, fontWeight = FontWeight.Bold, fontSize = 26.sp, lineHeight = 28.sp, fontFeatureSettings = "tnum")
}

/** Light "motion lab" theme; [night] = the black workout plate. */
@Composable
fun MotionForgeTheme(night: Boolean = false, content: @Composable () -> Unit) {
    val cs = if (night) nightScheme else scheme
    MaterialTheme(colorScheme = cs, typography = typography, shapes = shapes) {
        CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides cs.onBackground, content = content)
    }
}
