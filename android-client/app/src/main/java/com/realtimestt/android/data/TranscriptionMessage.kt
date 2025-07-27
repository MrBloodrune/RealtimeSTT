package com.realtimestt.android.data

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName

@Serializable
data class TranscriptionMessage(
    val type: MessageType,
    val text: String? = null,
    @SerialName("audio_file")
    val audioFile: String? = null,
    val timestamp: Long = System.currentTimeMillis()
)

@Serializable
enum class MessageType {
    @SerialName("partial")
    PARTIAL,
    
    @SerialName("realtime")
    REALTIME,
    
    @SerialName("full_sentence")
    FULL_SENTENCE,
    
    @SerialName("recording_start")
    RECORDING_START,
    
    @SerialName("recording_stop")
    RECORDING_STOP,
    
    @SerialName("audio_file")
    AUDIO_FILE,
    
    @SerialName("error")
    ERROR,
    
    @SerialName("info")
    INFO
}