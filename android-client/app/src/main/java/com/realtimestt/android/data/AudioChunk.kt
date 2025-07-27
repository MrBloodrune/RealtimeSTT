package com.realtimestt.android.data

data class AudioChunk(
    val data: ByteArray,
    val timestamp: Long = System.currentTimeMillis(),
    val sampleRate: Int = 16000,
    val channels: Int = 1,
    val bitsPerSample: Int = 16
) {
    val duration: Long
        get() = (data.size.toLong() * 1000) / (sampleRate * channels * (bitsPerSample / 8))
    
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as AudioChunk

        if (!data.contentEquals(other.data)) return false
        if (timestamp != other.timestamp) return false
        if (sampleRate != other.sampleRate) return false
        if (channels != other.channels) return false
        if (bitsPerSample != other.bitsPerSample) return false

        return true
    }

    override fun hashCode(): Int {
        var result = data.contentHashCode()
        result = 31 * result + timestamp.hashCode()
        result = 31 * result + sampleRate
        result = 31 * result + channels
        result = 31 * result + bitsPerSample
        return result
    }
}