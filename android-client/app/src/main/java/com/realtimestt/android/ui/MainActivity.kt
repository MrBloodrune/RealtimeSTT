package com.realtimestt.android.ui

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.IBinder
import android.view.MotionEvent
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.realtimestt.android.R
import com.realtimestt.android.data.ConnectionState
import com.realtimestt.android.data.MessageType
import com.realtimestt.android.data.RecordingMode
import com.realtimestt.android.data.RecordingState
import com.realtimestt.android.databinding.ActivityMainBinding
import com.realtimestt.android.services.AudioCaptureService
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private val viewModel: TranscriptionViewModel by viewModels()
    
    private var audioService: AudioCaptureService? = null
    private var serviceBound = false
    
    private val transcriptionBuilder = StringBuilder()
    
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            startAudioService()
        } else {
            Toast.makeText(this, R.string.permission_required, Toast.LENGTH_LONG).show()
        }
    }
    
    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, service: IBinder?) {
            val binder = service as AudioCaptureService.LocalBinder
            audioService = binder.getService()
            serviceBound = true
            
            // Set up audio listener
            audioService?.setAudioListener { audioChunk ->
                if (viewModel.isRecording.value) {
                    viewModel.sendAudioData(audioChunk.data)
                }
            }
            
            // Observe recording state
            audioService?.isRecording?.onEach { isRecording ->
                updateRecordingUI(isRecording)
            }?.launchIn(lifecycleScope)
        }
        
        override fun onServiceDisconnected(name: ComponentName?) {
            audioService = null
            serviceBound = false
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupUI()
        observeViewModel()
        checkPermissionAndStartService()
    }
    
    override fun onDestroy() {
        super.onDestroy()
        if (serviceBound) {
            unbindService(serviceConnection)
        }
    }
    
    private fun setupUI() {
        // Connect button
        binding.connectButton.setOnClickListener {
            val serverIp = binding.serverIpInput.text?.toString() ?: return@setOnClickListener
            
            if (viewModel.connectionState.value == ConnectionState.CONNECTED) {
                viewModel.disconnect()
            } else {
                viewModel.connect(serverIp)
            }
        }
        
        // Recording mode selection
        binding.recordingModeGroup.setOnCheckedChangeListener { _, checkedId ->
            val mode = when (checkedId) {
                R.id.pushToTalkMode -> RecordingMode.PUSH_TO_TALK
                R.id.continuousMode -> RecordingMode.CONTINUOUS
                R.id.vadMode -> RecordingMode.VOICE_ACTIVITY_DETECTION
                else -> RecordingMode.PUSH_TO_TALK
            }
            viewModel.setRecordingMode(mode)
            
            // Update record button behavior
            updateRecordButtonBehavior(mode)
        }
        
        // Clear button
        binding.clearButton.setOnClickListener {
            transcriptionBuilder.clear()
            binding.transcriptionText.text = getString(R.string.transcription_placeholder)
        }
        
        // Initial record button setup
        updateRecordButtonBehavior(RecordingMode.PUSH_TO_TALK)
    }
    
    private fun updateRecordButtonBehavior(mode: RecordingMode) {
        binding.recordButton.setOnTouchListener(null)
        binding.recordButton.setOnClickListener(null)
        
        when (mode) {
            RecordingMode.PUSH_TO_TALK -> {
                binding.recordButton.setOnTouchListener { _, event ->
                    when (event.action) {
                        MotionEvent.ACTION_DOWN -> {
                            startRecording()
                            true
                        }
                        MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                            stopRecording()
                            true
                        }
                        else -> false
                    }
                }
            }
            RecordingMode.CONTINUOUS -> {
                binding.recordButton.setOnClickListener {
                    if (viewModel.isRecording.value) {
                        stopRecording()
                    } else {
                        startRecording()
                    }
                }
            }
            RecordingMode.VOICE_ACTIVITY_DETECTION -> {
                binding.recordButton.setOnClickListener {
                    if (viewModel.isRecording.value) {
                        stopRecording()
                    } else {
                        startRecording()
                    }
                }
            }
        }
    }
    
    private fun observeViewModel() {
        // Connection state
        viewModel.connectionState.onEach { state ->
            updateConnectionUI(state)
        }.launchIn(lifecycleScope)
        
        // Transcription messages
        viewModel.transcriptionMessages.onEach { message ->
            when (message.type) {
                MessageType.PARTIAL -> {
                    // Update the last line with partial text
                    updatePartialTranscription(message.text ?: "")
                }
                MessageType.REALTIME -> {
                    // Update with stabilized text
                    updatePartialTranscription(message.text ?: "")
                }
                MessageType.FULL_SENTENCE -> {
                    // Add final transcription
                    addFinalTranscription(message.text ?: "")
                }
                MessageType.RECORDING_START -> {
                    // Visual feedback for VAD
                    binding.recordButton.setImageResource(R.drawable.ic_stop)
                }
                MessageType.RECORDING_STOP -> {
                    // Visual feedback for VAD
                    binding.recordButton.setImageResource(R.drawable.ic_mic)
                }
                else -> {
                    // Handle other message types if needed
                }
            }
        }.launchIn(lifecycleScope)
        
        // Recording state
        viewModel.recordingState.onEach { state ->
            when (state) {
                is RecordingState.Error -> {
                    Toast.makeText(this, state.message, Toast.LENGTH_SHORT).show()
                }
                else -> {}
            }
        }.launchIn(lifecycleScope)
    }
    
    private fun updateConnectionUI(state: ConnectionState) {
        val (statusText, statusColor) = when (state) {
            ConnectionState.DISCONNECTED -> {
                binding.connectButton.text = getString(R.string.connect)
                getString(R.string.connection_status, "Disconnected") to R.color.disconnected
            }
            ConnectionState.CONNECTING -> {
                binding.connectButton.text = getString(R.string.connect)
                getString(R.string.connection_status, "Connecting...") to R.color.connecting
            }
            ConnectionState.CONNECTED -> {
                binding.connectButton.text = getString(R.string.disconnect)
                getString(R.string.connection_status, "Connected") to R.color.connected
            }
            ConnectionState.RECONNECTING -> {
                binding.connectButton.text = getString(R.string.disconnect)
                getString(R.string.connection_status, "Reconnecting...") to R.color.connecting
            }
            ConnectionState.FAILED -> {
                binding.connectButton.text = getString(R.string.connect)
                getString(R.string.connection_status, "Failed") to R.color.disconnected
            }
        }
        
        binding.connectionStatus.text = statusText
        binding.connectionStatus.setTextColor(ContextCompat.getColor(this, statusColor))
    }
    
    private fun updateRecordingUI(isRecording: Boolean) {
        lifecycleScope.launch {
            if (viewModel.recordingMode.value == RecordingMode.CONTINUOUS) {
                binding.recordButton.setImageResource(
                    if (isRecording) R.drawable.ic_stop else R.drawable.ic_mic
                )
            }
        }
    }
    
    private var partialTextLine = ""
    
    private fun updatePartialTranscription(text: String) {
        partialTextLine = text
        updateTranscriptionDisplay()
    }
    
    private fun addFinalTranscription(text: String) {
        if (text.isNotBlank()) {
            transcriptionBuilder.appendLine(text)
            partialTextLine = ""
            updateTranscriptionDisplay()
        }
    }
    
    private fun updateTranscriptionDisplay() {
        val displayText = if (transcriptionBuilder.isEmpty() && partialTextLine.isEmpty()) {
            getString(R.string.transcription_placeholder)
        } else {
            transcriptionBuilder.toString() + partialTextLine
        }
        
        binding.transcriptionText.text = displayText
        binding.transcriptionText.setTextColor(
            if (displayText == getString(R.string.transcription_placeholder)) {
                ContextCompat.getColor(this, android.R.color.darker_gray)
            } else {
                ContextCompat.getColor(this, android.R.color.black)
            }
        )
    }
    
    private fun checkPermissionAndStartService() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED -> {
                startAudioService()
            }
            else -> {
                requestPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }
    }
    
    private fun startAudioService() {
        val serviceIntent = Intent(this, AudioCaptureService::class.java)
        startService(serviceIntent)
        bindService(serviceIntent, serviceConnection, Context.BIND_AUTO_CREATE)
    }
    
    private fun startRecording() {
        if (!serviceBound || audioService == null) return
        
        viewModel.startRecording()
        audioService?.startRecording()
    }
    
    private fun stopRecording() {
        if (!serviceBound || audioService == null) return
        
        viewModel.stopRecording()
        audioService?.stopRecording()
    }
}