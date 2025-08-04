'use client';

import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { 
  Trophy, 
  Star, 
  Zap, 
  MessageCircle, 
  Users, 
  Bell,
  X,
  CheckCircle,
  AlertCircle,
  Info,
  Gift
} from 'lucide-react';
import { useWebSocket } from '@/lib/websocket/websocket-provider';
import { cn } from '@/lib/utils';

interface Notification {
  id: string;
  type: string;
  payload: any;
  timestamp: string;
  priority?: string;
  read?: boolean;
}

interface LiveNotificationsProps {
  className?: string;
  maxNotifications?: number;
}

export function LiveNotifications({ className, maxNotifications = 5 }: LiveNotificationsProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showAll, setShowAll] = useState(false);
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    if (lastMessage) {
      // Check if this is a notification-worthy message
      if (isNotificationMessage(lastMessage)) {
        const notification: Notification = {
          id: `${Date.now()}-${Math.random()}`,
          type: lastMessage.type,
          payload: lastMessage.payload,
          timestamp: lastMessage.timestamp,
          priority: lastMessage.priority || 'normal',
          read: false
        };

        setNotifications(prev => {
          const updated = [notification, ...prev].slice(0, 20); // Keep max 20
          return updated;
        });

        // Play notification sound based on type
        playNotificationSound(lastMessage.type);

        // Auto-dismiss non-urgent notifications after 5 seconds
        if (notification.priority !== 'urgent' && notification.priority !== 'high') {
          setTimeout(() => {
            dismissNotification(notification.id);
          }, 5000);
        }
      }
    }
  }, [lastMessage]);

  const isNotificationMessage = (message: any): boolean => {
    const notificationTypes = [
      'xp_earned',
      'badge_unlocked',
      'level_up',
      'lesson_completed',
      'forum_new_answer',
      'peer_help_response',
      'study_session_created',
      'achievement_celebration',
      'system_announcement'
    ];
    
    return notificationTypes.includes(message.type);
  };

  const playNotificationSound = (type: string) => {
    // Create audio context for sound effects
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    
    const playTone = (frequency: number, duration: number, type: OscillatorType = 'sine') => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
      oscillator.type = type;
      
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + duration);
    };

    // Different sounds for different notification types
    switch (type) {
      case 'xp_earned':
        playTone(800, 0.2);
        break;
      case 'badge_unlocked':
        playTone(660, 0.3);
        setTimeout(() => playTone(880, 0.3), 100);
        break;
      case 'level_up':
        playTone(523, 0.2);
        setTimeout(() => playTone(659, 0.2), 150);
        setTimeout(() => playTone(784, 0.4), 300);
        break;
      case 'achievement_celebration':
        // Celebratory sound sequence
        [523, 659, 784, 1047].forEach((freq, i) => {
          setTimeout(() => playTone(freq, 0.2), i * 100);
        });
        break;
      default:
        playTone(600, 0.2);
    }
  };

  const dismissNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const markAsRead = (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'xp_earned':
        return <Zap className="h-5 w-5 text-yellow-500" />;
      case 'badge_unlocked':
        return <Trophy className="h-5 w-5 text-orange-500" />;
      case 'level_up':
        return <Star className="h-5 w-5 text-purple-500" />;
      case 'lesson_completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'forum_new_answer':
        return <MessageCircle className="h-5 w-5 text-blue-500" />;
      case 'study_session_created':
        return <Users className="h-5 w-5 text-indigo-500" />;
      case 'achievement_celebration':
        return <Gift className="h-5 w-5 text-pink-500" />;
      case 'system_announcement':
        return <Bell className="h-5 w-5 text-gray-500" />;
      default:
        return <Info className="h-5 w-5 text-gray-500" />;
    }
  };

  const getNotificationTitle = (notification: Notification): string => {
    const { type, payload } = notification;
    
    switch (type) {
      case 'xp_earned':
        return `+${payload.xp_amount} XP Earned!`;
      case 'badge_unlocked':
        return `Badge Unlocked: ${payload.badge?.name}`;
      case 'level_up':
        return `Level Up! Now Level ${payload.new_level}`;
      case 'lesson_completed':
        return 'Lesson Completed!';
      case 'forum_new_answer':
        return 'New Answer to Your Question';
      case 'study_session_created':
        return 'Study Session Available';
      case 'achievement_celebration':
        return 'Achievement Unlocked!';
      case 'system_announcement':
        return 'System Announcement';
      default:
        return 'Notification';
    }
  };

  const getNotificationMessage = (notification: Notification): string => {
    const { type, payload } = notification;
    
    switch (type) {
      case 'xp_earned':
        return payload.source || 'Great job!';
      case 'badge_unlocked':
        return payload.badge?.description || 'You unlocked a new badge!';
      case 'level_up':
        return `You now have ${payload.total_xp} total XP!`;
      case 'lesson_completed':
        return `Completed: ${payload.lesson_title}`;
      case 'forum_new_answer':
        return `"${payload.question?.title?.substring(0, 50)}..."`;
      case 'study_session_created':
        return `Topic: ${payload.topic}`;
      case 'achievement_celebration':
        return payload.achievement?.description || 'Congratulations!';
      case 'system_announcement':
        return payload.message;
      default:
        return payload.message || 'You have a new notification';
    }
  };

  const getPriorityColor = (priority: string = 'normal') => {
    switch (priority) {
      case 'urgent':
        return 'border-red-500 bg-red-50 dark:bg-red-900/20';
      case 'high':
        return 'border-orange-500 bg-orange-50 dark:bg-orange-900/20';
      case 'normal':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
      case 'low':
        return 'border-gray-500 bg-gray-50 dark:bg-gray-900/20';
      default:
        return 'border-gray-500 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;
  const displayNotifications = showAll ? notifications : notifications.slice(0, maxNotifications);

  return (
    <div className={cn("fixed top-4 right-4 z-50 w-96", className)}>
      {/* Notification Counter */}
      {unreadCount > 0 && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-6 w-6 flex items-center justify-center font-bold z-10"
        >
          {unreadCount}
        </motion.div>
      )}

      {/* Notifications List */}
      <AnimatePresence mode="popLayout">
        {displayNotifications.map((notification, index) => (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, x: 400, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 400, scale: 0.8 }}
            transition={{ 
              type: "spring", 
              stiffness: 300, 
              damping: 30,
              delay: index * 0.1 
            }}
            className={cn(
              "mb-3 p-4 rounded-lg border-l-4 shadow-lg backdrop-blur-sm",
              getPriorityColor(notification.priority),
              notification.read ? "opacity-70" : "",
              "cursor-pointer hover:shadow-xl transition-all duration-200"
            )}
            onClick={() => markAsRead(notification.id)}
          >
            <div className="flex items-start space-x-3">
              {/* Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {getNotificationIcon(notification.type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {getNotificationTitle(notification)}
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                      {getNotificationMessage(notification)}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      {new Date(notification.timestamp).toLocaleTimeString()}
                    </p>
                  </div>

                  {/* Dismiss Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      dismissNotification(notification.id);
                    }}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors ml-2"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {/* Special Animations for Celebrations */}
                {(notification.type === 'achievement_celebration' || 
                  notification.type === 'level_up' || 
                  notification.type === 'badge_unlocked') && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: [0, 1.2, 1] }}
                    transition={{ duration: 0.6 }}
                    className="absolute -top-2 -right-2 text-2xl"
                  >
                    🎉
                  </motion.div>
                )}
              </div>
            </div>

            {/* Progress Bar for XP */}
            {notification.type === 'xp_earned' && (
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: '100%' }}
                transition={{ duration: 1, delay: 0.5 }}
                className="mt-3 h-1 bg-yellow-300 rounded-full"
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Show More/Less Button */}
      {notifications.length > maxNotifications && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => setShowAll(!showAll)}
          className="w-full mt-2 py-2 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors text-center bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur-sm"
        >
          {showAll ? 'Show Less' : `Show ${notifications.length - maxNotifications} More`}
        </motion.button>
      )}

      {/* Clear All Button */}
      {notifications.length > 0 && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => setNotifications([])}
          className="w-full mt-2 py-2 text-xs text-red-500 hover:text-red-700 transition-colors text-center bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur-sm"
        >
          Clear All Notifications
        </motion.button>
      )}
    </div>
  );
}

// Hook for triggering custom notifications
export function useNotifications() {
  const triggerNotification = (type: string, payload: any, priority: string = 'normal') => {
    // This could dispatch to a global notification system
    const event = new CustomEvent('custom-notification', {
      detail: { type, payload, priority, timestamp: new Date().toISOString() }
    });
    window.dispatchEvent(event);
  };

  return { triggerNotification };
} 