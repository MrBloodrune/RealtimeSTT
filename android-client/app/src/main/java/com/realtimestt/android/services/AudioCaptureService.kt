package com.realtimestt.android.services

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.realtimestt.android.R
import com.realtimestt.android.data.AudioChunk
import com.realtimestt.android.ui.MainActivity
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.concurrent.LinkedBlockingQueue

class AudioCaptureService : Service() {
    
    companion object {
        private const val TAG = "AudioCaptureService"
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "audio_capture_channel"
        
        // Audio configuration
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val CHUNK_SIZE = 1024 // samples
        private const val BUFFER_SIZE_MULTIPLIER = 2
    }
    
    private val binder = LocalBinder()
    private var audioRecord: AudioRecord? = null
    private var recordingJob: Job? = null
    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    
    private var wakeLock: PowerManager.WakeLock? = null
    private val audioQueue = LinkedBlockingQueue<AudioChunk>(100)
    
    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording
    
    private val _recordingError = MutableStateFlow<String?>(null)
    val recordingError: StateFlow<String?> = _recordingError
    
    private var audioListener: ((AudioChunk) -> Unit)? = null
    
    inner class LocalBinder : Binder() {
        fun getService(): AudioCaptureService = this@AudioCaptureService
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        acquireWakeLock()
    }
    
    override fun onBind(intent: Intent): IBinder = binder
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, createNotification())
        return START_STICKY
    }
    
    override fun onDestroy() {
        super.onDestroy()
        stopRecording()
        releaseWakeLock()
        serviceScope.cancel()
    }
    
    fun startRecording() {
        if (_isRecording.value) {
            Log.w(TAG, "Already recording")
            return
        }
        
        if (!hasAudioPermission()) {
            _recordingError.value = "Microphone permission not granted"
            return
        }
        
        recordingJob = serviceScope.launch {
            try {
                initializeAudioRecord()
                audioRecord?.let { recorder ->
                    recorder.startRecording()
                    _isRecording.value = true
                    _recordingError.value = null
                    
                    val bufferSize = CHUNK_SIZE * 2 // 16-bit = 2 bytes per sample
                    val buffer = ByteArray(bufferSize)
                    
                    while (isActive && _isRecording.value) {
                        val bytesRead = recorder.read(buffer, 0, bufferSize)
                        
                        if (bytesRead > 0) {
                            val audioChunk = AudioChunk(
                                data = buffer.copyOf(bytesRead),
                                sampleRate = SAMPLE_RATE,
                                channels = 1,
                                bitsPerSample = 16
                            )
                            
                            // Notify listener safely
                            try {
                                withContext(Dispatchers.Main) {
                                    audioListener?.invoke(audioChunk)
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "Error notifying listener", e)
                            }
                            
                            // Add to queue (drop old chunks if full)
                            if (!audioQueue.offer(audioChunk)) {
                                audioQueue.poll() // Remove oldest
                                audioQueue.offer(audioChunk)
                            }
                        } else if (bytesRead < 0) {
                            Log.e(TAG, "AudioRecord read error: $bytesRead")
                            _recordingError.value = "Audio read error: $bytesRead"
                            break
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Recording error", e)
                _recordingError.value = e.message
            } finally {
                _isRecording.value = false
                audioRecord?.stop()
            }
        }
    }
    
    fun stopRecording() {
        _isRecording.value = false
        recordingJob?.cancel()
        recordingJob = null
        audioRecord?.apply {
            stop()
            release()
        }
        audioRecord = null
        audioQueue.clear()
    }
    
    fun setAudioListener(listener: ((AudioChunk) -> Unit)?) {
        audioListener = listener
    }
    
    fun getQueuedAudio(): List<AudioChunk> {
        return audioQueue.toList()
    }
    
    fun clearAudioQueue() {
        audioQueue.clear()
    }
    
    private fun initializeAudioRecord() {
        val minBufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT
        )
        
        if (minBufferSize == AudioRecord.ERROR || minBufferSize == AudioRecord.ERROR_BAD_VALUE) {
            throw IllegalStateException("Failed to get minimum buffer size")
        }
        
        val bufferSize = minBufferSize * BUFFER_SIZE_MULTIPLIER
        
        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT,
            bufferSize
        ).apply {
            if (state != AudioRecord.STATE_INITIALIZED) {
                release()
                throw IllegalStateException("Failed to initialize AudioRecord")
            }
        }
    }
    
    private fun hasAudioPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Audio Capture Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "RealtimeSTT audio capture service"
                setShowBadge(false)
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("RealtimeSTT")
            .setContentText("Audio capture active")
            .setSmallIcon(R.drawable.ic_mic)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }
    
    private fun acquireWakeLock() {
        val powerManager = getSystemService(PowerManager::class.java)
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "RealtimeSTT::AudioCaptureWakeLock"
        ).apply {
            acquire(10 * 60 * 1000L) // 10 minutes timeout
        }
    }
    
    private fun releaseWakeLock() {
        wakeLock?.apply {
            if (isHeld) {
                release()
            }
        }
        wakeLock = null
    }
}