package com.realtimestt.android.data

sealed class RecordingState {
    object Idle : RecordingState()
    object Recording : RecordingState()
    object Processing : RecordingState()
    data class Error(val message: String) : RecordingState()
}

enum class RecordingMode {
    PUSH_TO_TALK,
    CONTINUOUS,
    VOICE_ACTIVITY_DETECTION
}