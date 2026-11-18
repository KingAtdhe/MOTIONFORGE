import java.net.URI
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
}

android {
    namespace = "eu.motionforge.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "eu.motionforge.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 4
        versionName = "0.3.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    androidResources {
        // MediaPipe memory-maps the model; Filament reads GLB bytes. Keep both uncompressed.
        noCompress += listOf("task", "glb")
    }

    packaging {
        jniLibs {
            // Guard in case MediaPipe and Filament ever both ship the shared C++ runtime.
            pickFirsts += "**/libc++_shared.so"
        }
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

// ---------------------------------------------------------------------------
// MediaPipe Pose Landmarker model (Apache-2.0, published by Google).
// Downloaded at build time instead of being committed. If the download fails the
// app still builds, and the camera spike shows an honest "pose model unavailable"
// state. CI passes -Pmotionforge.requirePoseModel=true so a missing model fails CI.
// ---------------------------------------------------------------------------
val poseModelUrl =
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
val poseModelFile = file("src/main/assets/models/pose_landmarker_lite.task")
val requirePoseModel = providers.gradleProperty("motionforge.requirePoseModel").map { it.toBoolean() }.orElse(false)

val downloadPoseModel by tasks.registering {
    group = "motionforge"
    description = "Downloads the MediaPipe pose_landmarker_lite.task model into app assets."
    val out = poseModelFile
    val url = poseModelUrl
    val required = requirePoseModel
    outputs.file(out)
    outputs.upToDateWhen { out.exists() && out.length() > 1_000_000L }
    doLast {
        if (out.exists() && out.length() > 1_000_000L) return@doLast
        out.parentFile.mkdirs()
        val part = File(out.parentFile, out.name + ".part")
        try {
            URI(url).toURL().openStream().use { input ->
                part.outputStream().use { output -> input.copyTo(output) }
            }
            check(part.length() > 1_000_000L) { "Downloaded pose model is unexpectedly small (${part.length()} bytes)" }
            if (out.exists()) out.delete()
            check(part.renameTo(out)) { "Could not move pose model into place" }
            logger.lifecycle("MOTIONFORGE: pose model downloaded (${out.length()} bytes)")
        } catch (e: Exception) {
            part.delete()
            if (required.get()) throw GradleException("Pose model download failed: ${e.message}", e)
            logger.warn("MOTIONFORGE WARNING: pose model not downloaded (${e.message}). Pose spike will report the model as unavailable.")
        }
    }
}

tasks.named("preBuild") { dependsOn(downloadPoseModel) }

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.core)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)

    implementation(libs.mediapipe.tasks.vision)

    implementation(libs.filament.android)
    implementation(libs.filament.gltfio.android)
    implementation(libs.filament.utils.android)

    implementation(libs.kotlinx.serialization.json)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    testImplementation(libs.junit)
}
