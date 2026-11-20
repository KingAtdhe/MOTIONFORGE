package eu.motionforge.app.core.design

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
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

/**
 * MOTIONFORGE identity: a cool, light gym-floor ground with white "mat" surfaces and deep ink type; cobalt for
 * fitness and primary actions, glove red for fighting fundamentals. The workout itself runs on a dark "night"
 * scheme so the camera and the coach stand out. Colour is always paired with text, never the only signal.
 */
object MfColors {
    val Ground = Color(0xFFECEFF3)
    val Paper = Color(0xFFFFFFFF)
    val Ink = Color(0xFF121826)
    val Slate = Color(0xFF5A6472)
    val Rule = Color(0xFFD6DBE2)
    val Cobalt = Color(0xFF2F4BF5)
    val Glove = Color(0xFFE2343F)

    // status colours, dark enough to read as text on the light ground
    val Signal = Color(0xFF0B8A63)
    val Caution = Color(0xFFA35F00)
    val Halt = Color(0xFFC62828)

    // the workout screen's dark scheme
    val Night = Color(0xFF0E1320)
    val NightRaised = Color(0xFF1B2335)
    val NightRule = Color(0xFF2C3549)
    val OnNight = Color(0xFFF2F4F7)
    val OnNightMuted = Color(0xFF9AA4B5)
    val CautionOnNight = Color(0xFFF2B544)
    val SignalOnNight = Color(0xFF5EEAD4)
}

/** Category colour (always paired with a text label). */
val TrainingCategory.accent: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> MfColors.Cobalt
        TrainingCategory.FIGHTING_FUNDAMENTALS -> MfColors.Glove
    }

/** Lighter category colour for text and rings on the dark workout scheme. */
val TrainingCategory.accentOnNight: Color
    get() = when (this) {
        TrainingCategory.FITNESS -> Color(0xFF8193FF)
        TrainingCategory.FIGHTING_FUNDAMENTALS -> Color(0xFFFF6B73)
    }

/** Big Shoulders Display for headings, numbers and the exercise-name backdrops; Schibsted Grotesk for reading. */
val DisplayFont = FontFamily(
    Font(R.font.big_shoulders_display_extrabold, FontWeight.ExtraBold),
    Font(R.font.big_shoulders_display_black, FontWeight.Black),
)
val BodyFont = FontFamily(
    Font(R.font.schibsted_grotesk_regular, FontWeight.Normal),
    Font(R.font.schibsted_grotesk_medium, FontWeight.Medium),
    Font(R.font.schibsted_grotesk_bold, FontWeight.Bold),
)

private val lightScheme = lightColorScheme(
    primary = MfColors.Cobalt,
    onPrimary = Color.White,
    secondary = MfColors.Glove,
    onSecondary = Color.White,
    background = MfColors.Ground,
    onBackground = MfColors.Ink,
    surface = MfColors.Paper,
    onSurface = MfColors.Ink,
    surfaceVariant = Color(0xFFE2E6EC),
    onSurfaceVariant = MfColors.Slate,
    secondaryContainer = Color(0xFFDDE3FF),
    onSecondaryContainer = MfColors.Cobalt,
    outline = MfColors.Rule,
    outlineVariant = MfColors.Rule,
    error = MfColors.Halt,
    onError = Color.White,
)

private val nightScheme = darkColorScheme(
    primary = Color(0xFF6D82FF),
    onPrimary = Color.White,
    secondary = Color(0xFFFF5A64),
    onSecondary = Color.White,
    background = MfColors.Night,
    onBackground = MfColors.OnNight,
    surface = MfColors.NightRaised,
    onSurface = MfColors.OnNight,
    surfaceVariant = MfColors.NightRaised,
    onSurfaceVariant = MfColors.OnNightMuted,
    outline = MfColors.NightRule,
    outlineVariant = MfColors.NightRule,
    error = Color(0xFFFF6B6B),
    onError = MfColors.Night,
)

private val typography = Typography(
    // display sizes: Big Shoulders is narrow, so it carries large sizes without wrapping on a phone
    displayLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Black, fontSize = 96.sp, lineHeight = 88.sp),
    displayMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Black, fontSize = 64.sp, lineHeight = 60.sp),
    displaySmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 44.sp, lineHeight = 44.sp),
    headlineLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Black, fontSize = 40.sp, lineHeight = 42.sp),
    headlineMedium = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.Black, fontSize = 32.sp, lineHeight = 34.sp),
    headlineSmall = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 26.sp, lineHeight = 28.sp),
    titleLarge = TextStyle(fontFamily = DisplayFont, fontWeight = FontWeight.ExtraBold, fontSize = 24.sp, lineHeight = 26.sp),
    titleMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Bold, fontSize = 17.sp, lineHeight = 23.sp),
    titleSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Bold, fontSize = 15.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontFamily = BodyFont, fontSize = 17.sp, lineHeight = 26.sp),
    bodyMedium = TextStyle(fontFamily = BodyFont, fontSize = 15.sp, lineHeight = 22.sp),
    bodySmall = TextStyle(fontFamily = BodyFont, fontSize = 13.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Bold, fontSize = 15.sp, lineHeight = 20.sp),
    labelMedium = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 18.sp),
    labelSmall = TextStyle(fontFamily = BodyFont, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp),
)

private val shapes = Shapes(
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(28.dp),
)

/** [night] = the dark workout scheme (running session, camera). */
@Composable
fun MotionForgeTheme(night: Boolean = false, content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (night) nightScheme else lightScheme, typography = typography, shapes = shapes, content = content)
}
