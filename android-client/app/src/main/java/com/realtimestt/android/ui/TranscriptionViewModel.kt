package com.realtimestt.android.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.realtimestt.android.data.*
import com.realtimestt.android.network.WebSocketManager
import com.realtimestt.android.utils.AudioBufferManager
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class TranscriptionViewModel : ViewModel() {
    
    private var webSocketManager = WebSocketManager()
    private val audioBufferManager = AudioBufferManager()
    
    private val _recordingState = MutableStateFlow<RecordingState>(RecordingState.Idle)
    val recordingState: StateFlow<RecordingState> = _recordingState.asStateFlow()
    
    private val _recordingMode = MutableStateFlow(RecordingMode.PUSH_TO_TALK)
    val recordingMode: StateFlow<RecordingMode> = _recordingMode.asStateFlow()
    
    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()
    
    private val _transcriptionMessages = MutableSharedFlow<TranscriptionMessage>()
    val transcriptionMessages: SharedFlow<TranscriptionMessage> = _transcriptionMessages.asSharedFlow()
    
    val connectionState: StateFlow<ConnectionState> = webSocketManager.connectionState
    val connectionError: StateFlow<String?> = webSocketManager.lastError
    
    init {
        // Set up WebSocket message listener
        webSocketManager.setMessageListener { message ->
            viewModelScope.launch {
                _transcriptionMessages.emit(message)
                
                // Handle VAD mode
                if (_recordingMode.value == RecordingMode.VOICE_ACTIVITY_DETECTION) {
                    when (message.type) {
                        MessageType.RECORDING_START -> {
                            // Server detected voice activity
                            _isRecording.value = true
                        }
                        MessageType.RECORDING_STOP -> {
                            // Server detected end of voice activity
                            _isRecording.value = false
                        }
                        else -> {}
                    }
                }
            }
        }
        
        // Monitor connection state for auto-reconnect in continuous mode
        connectionState.onEach { state ->
            if (state == ConnectionState.CONNECTED && 
                _recordingMode.value == RecordingMode.CONTINUOUS && 
                _isRecording.value) {
                // Resume sending audio after reconnection
                sendQueuedAudio()
            }
        }.launchIn(viewModelScope)
    }
    
    fun connect(serverIp: String) {
        val config = ServerConfig(host = serverIp)
        webSocketManager.destroy()
        
        // Create new instance with updated config
        webSocketManager = WebSocketManager(config)
        
        // Set up message listener again
        webSocketManager.setMessageListener { message ->
            viewModelScope.launch {
                _transcriptionMessages.emit(message)
                
                // Handle VAD mode
                if (_recordingMode.value == RecordingMode.VOICE_ACTIVITY_DETECTION) {
                    when (message.type) {
                        MessageType.RECORDING_START -> {
                            // Server detected voice activity
                            _isRecording.value = true
                        }
                        MessageType.RECORDING_STOP -> {
                            // Server detected end of voice activity
                            _isRecording.value = false
                        }
                        else -> {}
                    }
                }
            }
        }
        
        webSocketManager.connect()
    }
    
    fun disconnect() {
        stopRecording()
        webSocketManager.disconnect()
    }
    
    fun setRecordingMode(mode: RecordingMode) {
        _recordingMode.value = mode
        
        // Stop recording if switching modes while recording
        if (_isRecording.value) {
            stopRecording()
        }
    }
    
    fun startRecording() {
        if (connectionState.value != ConnectionState.CONNECTED) {
            _recordingState.value = RecordingState.Error("Not connected to server")
            return
        }
        
        _isRecording.value = true
        _recordingState.value = RecordingState.Recording
        
        // Clear audio buffer when starting new recording
        viewModelScope.launch {
            audioBufferManager.clear()
        }
    }
    
    fun stopRecording() {
        _isRecording.value = false
        _recordingState.value = RecordingState.Idle
        
        // Send any remaining audio
        viewModelScope.launch {
            sendQueuedAudio()
        }
    }
    
    fun sendAudioData(audioData: ByteArray) {
        if (connectionState.value == ConnectionState.CONNECTED) {
            webSocketManager.sendAudioData(audioData)
        } else {
            // Buffer audio for later sending
            viewModelScope.launch {
                val chunk = AudioChunk(data = audioData)
                audioBufferManager.addChunk(chunk)
            }
        }
    }
    
    private suspend fun sendQueuedAudio() {
        val chunks = audioBufferManager.getAllChunks()
        chunks.forEach { chunk ->
            webSocketManager.sendAudioData(chunk.data)
        }
    }
    
    override fun onCleared() {
        super.onCleared()
        webSocketManager.destroy()
    }
}