package com.realtimestt.android.network

import android.util.Log
import com.realtimestt.android.data.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import kotlinx.serialization.decodeFromString
import okhttp3.*
import okio.ByteString
import java.util.concurrent.TimeUnit
import java.util.concurrent.LinkedBlockingQueue
import kotlin.math.min

class WebSocketManager(
    private val serverConfig: ServerConfig = ServerConfig()
) {
    companion object {
        private const val TAG = "WebSocketManager"
        private const val NORMAL_CLOSURE_STATUS = 1000
        private const val MAX_QUEUE_SIZE = 1000
        private const val INITIAL_RECONNECT_DELAY = 1000L
        private const val MAX_RECONNECT_DELAY = 30000L
    }
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS)
        .pingInterval(30, TimeUnit.SECONDS)
        .build()
    
    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var reconnectJob: Job? = null
    private var reconnectAttempts = 0
    private var reconnectDelay = INITIAL_RECONNECT_DELAY
    
    private val messageQueue = LinkedBlockingQueue<ByteArray>(MAX_QUEUE_SIZE)
    
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState
    
    private val _lastError = MutableStateFlow<String?>(null)
    val lastError: StateFlow<String?> = _lastError
    
    private var messageListener: ((TranscriptionMessage) -> Unit)? = null
    
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }
    
    fun connect() {
        if (_connectionState.value == ConnectionState.CONNECTED || 
            _connectionState.value == ConnectionState.CONNECTING) {
            Log.w(TAG, "Already connected or connecting")
            return
        }
        
        _connectionState.value = ConnectionState.CONNECTING
        _lastError.value = null
        
        val request = Request.Builder()
            .url(serverConfig.websocketUrl)
            .build()
        
        webSocket = client.newWebSocket(request, createWebSocketListener())
    }
    
    fun disconnect() {
        reconnectJob?.cancel()
        reconnectJob = null
        reconnectAttempts = 0
        
        webSocket?.close(NORMAL_CLOSURE_STATUS, "Client disconnecting")
        webSocket = null
        
        _connectionState.value = ConnectionState.DISCONNECTED
        messageQueue.clear()
    }
    
    fun sendAudioData(audioData: ByteArray) {
        if (_connectionState.value != ConnectionState.CONNECTED) {
            // Queue the message if not connected
            if (!messageQueue.offer(audioData)) {
                // Queue is full, drop oldest message
                messageQueue.poll()
                messageQueue.offer(audioData)
            }
            return
        }
        
        webSocket?.send(ByteString.of(*audioData))
    }
    
    fun setMessageListener(listener: ((TranscriptionMessage) -> Unit)?) {
        messageListener = listener
    }
    
    private fun createWebSocketListener() = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.i(TAG, "WebSocket connected")
            _connectionState.value = ConnectionState.CONNECTED
            _lastError.value = null
            reconnectAttempts = 0
            reconnectDelay = INITIAL_RECONNECT_DELAY
            
            // Send queued messages
            scope.launch {
                while (messageQueue.isNotEmpty() && _connectionState.value == ConnectionState.CONNECTED) {
                    messageQueue.poll()?.let { data ->
                        webSocket.send(ByteString.of(*data))
                    }
                    delay(10) // Small delay to avoid overwhelming the server
                }
            }
        }
        
        override fun onMessage(webSocket: WebSocket, text: String) {
            try {
                val message = json.decodeFromString<TranscriptionMessage>(text)
                scope.launch(Dispatchers.Main) {
                    messageListener?.invoke(message)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to parse message: $text", e)
            }
        }
        
        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            // Handle binary messages if needed
            Log.d(TAG, "Received binary message: ${bytes.size} bytes")
        }
        
        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            Log.i(TAG, "WebSocket closing: $code $reason")
            webSocket.close(NORMAL_CLOSURE_STATUS, null)
        }
        
        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.i(TAG, "WebSocket closed: $code $reason")
            _connectionState.value = ConnectionState.DISCONNECTED
            
            // Attempt reconnection if not a normal closure
            if (code != NORMAL_CLOSURE_STATUS) {
                scheduleReconnect()
            }
        }
        
        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e(TAG, "WebSocket failure: ${t.message}", t)
            Log.e(TAG, "Response: ${response?.code} - ${response?.message}")
            _lastError.value = "Connection failed: ${t.message ?: "Unknown error"}"
            _connectionState.value = ConnectionState.FAILED
            
            scheduleReconnect()
        }
    }
    
    private fun scheduleReconnect() {
        if (reconnectAttempts >= serverConfig.maxReconnectAttempts) {
            Log.e(TAG, "Max reconnection attempts reached")
            _connectionState.value = ConnectionState.FAILED
            return
        }
        
        _connectionState.value = ConnectionState.RECONNECTING
        reconnectAttempts++
        
        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            Log.i(TAG, "Reconnecting in ${reconnectDelay}ms (attempt $reconnectAttempts)")
            delay(reconnectDelay)
            
            // Exponential backoff
            reconnectDelay = min(reconnectDelay * 2, MAX_RECONNECT_DELAY)
            
            if (isActive) {
                connect()
            }
        }
    }
    
    fun destroy() {
        disconnect()
        scope.cancel()
        client.dispatcher.executorService.shutdown()
    }
}