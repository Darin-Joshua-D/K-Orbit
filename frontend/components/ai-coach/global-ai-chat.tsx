'use client';

import { AIChat, useAIChat } from './ai-chat';
import { useAuth } from '@/lib/auth/auth-provider';

export function GlobalAIChat() {
  const { user } = useAuth();
  const { isMinimized, toggleMinimize } = useAIChat();

  // Only show AI Chat if user is authenticated
  if (!user) {
    return null;
  }

  return (
    <AIChat 
      isMinimized={isMinimized}
      onToggleMinimize={toggleMinimize}
      className="fixed bottom-4 right-4 z-50"
    />
  );
} 