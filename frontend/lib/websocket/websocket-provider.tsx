'use client';

import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { useAuth } from '@/lib/auth/auth-provider';

interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

interface WebSocketContextType {
  isConnected: boolean;
  sendMessage: (message: any) => void;
  subscribe: (room: string) => void;
  unsubscribe: (room: string) => void;
  lastMessage: WebSocketMessage | null;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { user, session } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (user && session?.access_token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, session]);

  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
      const token = session?.access_token;
      
      if (!token) {
        console.warn('No access token available for WebSocket connection');
        return;
      }

      wsRef.current = new WebSocket(`${wsUrl}/ws/notifications?token=${token}`);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        
        // Start heartbeat
        startHeartbeat();
        
        // Clear any reconnection attempts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
          
          // Handle specific message types
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        stopHeartbeat();
        
        // Attempt to reconnect after delay (unless it was a manual close)
        if (event.code !== 1000 && user) {
          scheduleReconnect();
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      scheduleReconnect();
    }
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    
    setIsConnected(false);
    stopHeartbeat();
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  };

  const scheduleReconnect = () => {
    if (reconnectTimeoutRef.current) {
      return; // Already scheduled
    }
    
    const delay = 5000; // 5 seconds
    console.log(`Scheduling WebSocket reconnection in ${delay}ms`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectTimeoutRef.current = null;
      if (user) {
        connect();
      }
    }, delay);
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendMessage({
          type: 'ping',
          timestamp: new Date().toISOString(),
        });
      }
    }, 30000); // 30 seconds
  };

  const stopHeartbeat = () => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  };

  const sendMessage = (message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  };

  const subscribe = (room: string) => {
    sendMessage({
      type: 'subscribe',
      room: room,
    });
  };

  const unsubscribe = (room: string) => {
    sendMessage({
      type: 'unsubscribe',
      room: room,
    });
  };

  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'xp_earned':
        // Handle XP notification
        console.log('XP earned:', message.payload);
        break;
      
      case 'badge_earned':
        // Handle badge notification
        console.log('Badge earned:', message.payload);
        break;
      
      case 'forum_notification':
        // Handle forum notification
        console.log('Forum notification:', message.payload);
        break;
      
      case 'course_notification':
        // Handle course notification
        console.log('Course notification:', message.payload);
        break;
      
      case 'system_notification':
        // Handle system notification
        console.log('System notification:', message.payload);
        break;
      
      case 'pong':
        // Heartbeat response
        break;
      
      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const value = {
    isConnected,
    sendMessage,
    subscribe,
    unsubscribe,
    lastMessage,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

// Hook for subscribing to specific rooms
export function useWebSocketSubscription(room: string) {
  const { subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (isConnected && room) {
      subscribe(room);
      
      return () => {
        unsubscribe(room);
      };
    }
  }, [isConnected, room, subscribe, unsubscribe]);
} 