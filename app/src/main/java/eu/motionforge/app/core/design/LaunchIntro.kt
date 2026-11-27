package eu.motionforge.app.core.design

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.dp
import eu.motionforge.app.R
import kotlinx.coroutines.launch

/**
 * The app's own launch art, right after the system launch screen (which can only show the icon): the pair from the
 * owner's flexing-poses sheet rising in on the black plate, the wordmark under them, about a second in all, then it
 * fades into the app. A tap skips it. With "remove animations" on it shows the finished picture briefly, no motion.
 * Decorative only: hidden from screen readers, which go straight to the app.
 */
@Composable
fun LaunchIntro(onDone: () -> Unit) {
    val reduce = rememberReduceMotion()
    val figure = remember { Animatable(if (reduce) 1f else 0f) }
    val word = remember { Animatable(if (reduce) 1f else 0f) }
    val shown = remember { Animatable(1f) }
    // every step is an animation on the frame clock (no plain delays), so UI tests run straight through it
    LaunchedEffect(Unit) {
        if (!reduce) {
            launch { figure.animateTo(1f, tween(450, easing = FastOutSlowInEasing)) }
            word.animateTo(1f, tween(250, delayMillis = 300))
        }
        shown.animateTo(0f, tween(if (reduce) 1 else 250, delayMillis = if (reduce) 600 else 500))
        onDone()
    }
    Box(
        Modifier.fillMaxSize()
            .graphicsLayer { alpha = shown.value }
            .background(Color.Black)
            .clearAndSetSemantics {}
            .pointerInput(Unit) { detectTapGestures { onDone() } },
    ) {
        Image(
            painterResource(R.drawable.launch_duo), contentDescription = null, contentScale = ContentScale.Fit,
            modifier = Modifier.align(Alignment.Center).fillMaxWidth().aspectRatio(1f)
                .graphicsLayer { alpha = figure.value; translationY = (1f - figure.value) * 14.dp.toPx() },
        )
        Image(
            painterResource(R.drawable.splash_branding), contentDescription = null,
            modifier = Modifier.align(Alignment.BottomCenter).navigationBarsPadding().padding(bottom = 48.dp)
                .size(200.dp, 80.dp).graphicsLayer { alpha = word.value },
        )
    }
}
