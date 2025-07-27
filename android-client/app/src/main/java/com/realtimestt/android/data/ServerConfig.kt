package com.realtimestt.android.data

data class ServerConfig(
    val host: String = "192.168.1.100",
    val port: Int = 9999,
    val reconnectInterval: Long = 5000,
    val maxReconnectAttempts: Int = 10
) {
    val websocketUrl: String
        get() = "ws://$host:$port"
}