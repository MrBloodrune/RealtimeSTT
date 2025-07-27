package com.realtimestt.android.utils

import com.realtimestt.android.data.AudioChunk
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.concurrent.ConcurrentLinkedQueue

class AudioBufferManager(
    private val maxQueueSize: Int = 100,
    private val maxQueueDurationMs: Long = 5000
) {
    private val audioQueue = ConcurrentLinkedQueue<AudioChunk>()
    private val mutex = Mutex()
    
    suspend fun addChunk(chunk: AudioChunk): Boolean = mutex.withLock {
        // Remove old chunks that exceed duration limit
        val currentTime = System.currentTimeMillis()
        while (audioQueue.isNotEmpty()) {
            val oldest = audioQueue.peek()
            if (oldest != null && currentTime - oldest.timestamp > maxQueueDurationMs) {
                audioQueue.poll()
            } else {
                break
            }
        }
        
        // Check queue size limit
        if (audioQueue.size >= maxQueueSize) {
            audioQueue.poll() // Remove oldest
        }
        
        audioQueue.offer(chunk)
    }
    
    suspend fun getNextChunk(): AudioChunk? = mutex.withLock {
        audioQueue.poll()
    }
    
    suspend fun getAllChunks(): List<AudioChunk> = mutex.withLock {
        val chunks = audioQueue.toList()
        audioQueue.clear()
        chunks
    }
    
    suspend fun clear() = mutex.withLock {
        audioQueue.clear()
    }
    
    fun size(): Int = audioQueue.size
    
    fun getTotalDuration(): Long {
        return audioQueue.sumOf { it.duration }
    }
    
    fun isEmpty(): Boolean = audioQueue.isEmpty()
    
    fun isNotEmpty(): Boolean = audioQueue.isNotEmpty()
}