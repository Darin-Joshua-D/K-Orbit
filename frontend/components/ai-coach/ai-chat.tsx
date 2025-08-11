'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Sparkles, FileText, Brain, AlertCircle, Paperclip } from 'lucide-react';
import { useAuth } from '@/lib/auth/auth-provider';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '@/lib/utils';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    sources?: string[];
    confidence?: number;
    tokens?: number;
    feature?: 'knowledge' | 'quiz' | 'suggestions' | 'learning_path' | 'feedback';
  };
  createdAt: Date;
}

interface ChatConversation {
  id: string;
  title: string;
  messageCount: number;
  lastMessageAt: Date;
}

interface AIChatProps {
  className?: string;
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
}

export function AIChat({ className, isMinimized = false, onToggleMinimize }: AIChatProps) {
  const { user } = useAuth();
  const [message, setMessage] = useState('');
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch conversation messages
  const { data: messages = [], isLoading: isLoadingMessages, error: messagesError } = useQuery({
    queryKey: ['chat-messages', currentConversationId],
    queryFn: async () => {
      if (!currentConversationId) return [];
      
      const response = await fetch(`/api/ai/conversations/${currentConversationId}/messages`, {
        headers: {
          'Authorization': `Bearer ${user?.session?.access_token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch messages: ${response.status}`);
      }
      return response.json();
    },
    enabled: !!currentConversationId && !!user,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user?.session?.access_token}`,
        },
        body: JSON.stringify({
          message: content,
          conversation_id: currentConversationId,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `HTTP ${response.status}: Failed to send message`);
      }
      return response.json();
    },
    onSuccess: (data) => {
      // Clear any previous errors
      setError(null);
      
      // Update conversation ID if it's a new conversation
      if (!currentConversationId) {
        setCurrentConversationId(data.conversation_id);
      }
      
      // Invalidate and refetch messages
      queryClient.invalidateQueries({ queryKey: ['chat-messages', data.conversation_id] });
      setMessage('');
      // Keep attachments UI-only; clear selection after send
      setAttachedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    onError: (error: Error) => {
      console.error('Failed to send message:', error);
      setError(error.message);
    },
  });

  const handleSendMessage = async () => {
    if (!message.trim() || sendMessageMutation.isPending) return;
    
    const messageContent = message.trim();
    setMessage('');
    setError(null);
    
    try {
      await sendMessageMutation.mutateAsync(messageContent);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessage(messageContent); // Restore message on error
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Dummy file upload UI handlers (no network calls)
  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setAttachedFiles(files);
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Quick action buttons
  const quickActions = [
    {
      label: 'Ask about onboarding',
      icon: FileText,
      message: 'What are the key steps in our company onboarding process?'
    },
    {
      label: 'Find training resources',
      icon: Brain,
      message: 'Can you help me find relevant training materials for my role?'
    },
    {
      label: 'Company policies',
      icon: FileText,
      message: 'What are our main company policies I should be aware of?'
    }
  ];

  if (isMinimized) {
    return (
      <div className={cn("fixed bottom-4 right-4 z-50", className)}>
        <button
          onClick={onToggleMinimize}
          className="bg-primary text-white p-4 rounded-full shadow-lg hover:bg-primary/90 transition-all duration-200 hover:scale-105 relative"
        >
          <Bot className="h-6 w-6" />
          <span className="absolute -top-1 -right-1 h-3 w-3 bg-green-500 rounded-full animate-pulse" />
          {error && (
            <span className="absolute -top-1 -left-1 h-3 w-3 bg-red-500 rounded-full" />
          )}
        </button>
      </div>
    );
  }

  return (
    <div className={cn(
      "fixed bottom-4 right-4 w-96 h-[600px] glass-card dark:glass-card-dark flex flex-col z-50 overflow-hidden",
      className
    )}>
      {/* Chat Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/20 dark:border-white/10 bg-gradient-to-r from-primary/20 to-blue-500/20 backdrop-blur-sm">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white dark:border-gray-900" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">K-Orbit Coach</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">AI Learning Assistant</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Sparkles className="h-4 w-4 text-primary animate-pulse" />
          <button
            onClick={onToggleMinimize}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Error Display */}
        {(error || messagesError) && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-4">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
              <span className="text-sm text-red-700 dark:text-red-300">
                {error || messagesError?.message || 'Something went wrong'}
              </span>
            </div>
          </div>
        )}

        {messages.length === 0 && !isLoadingMessages && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-gradient-to-br from-primary/20 to-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Bot className="h-8 w-8 text-primary" />
            </div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Welcome to K-Orbit Coach!</h4>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              I'm here to help you with learning, company policies, and any questions about your journey.
            </p>
            
            {/* Quick Actions */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">
                Quick Actions
              </p>
              {quickActions.map((action, index) => {
                const IconComponent = action.icon;
                return (
                  <button
                    key={index}
                    onClick={() => setMessage(action.message)}
                    className="w-full text-left p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
                  >
                    <div className="flex items-center space-x-2">
                      <IconComponent className="h-4 w-4 text-gray-400 group-hover:text-primary transition-colors" />
                      <span className="text-sm text-gray-600 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                        {action.label}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoadingMessages && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}

        {/* Existing Messages */}
        {messages.map((msg: ChatMessage) => (
          <div
            key={msg.id}
            className={cn(
              "flex items-start space-x-3",
              msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            )}
          >
            {/* Avatar */}
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
              msg.role === 'user'
                ? 'bg-gray-100 dark:bg-gray-800'
                : 'bg-gradient-to-br from-primary to-blue-600'
            )}>
              {msg.role === 'user' ? (
                <User className="h-4 w-4 text-gray-600 dark:text-gray-300" />
              ) : (
                <Bot className="h-4 w-4 text-white" />
              )}
            </div>

            {/* Message Content */}
            <div className={cn(
              "flex-1 max-w-[80%]",
              msg.role === 'user' ? 'text-right' : ''
            )}>
              <div className={cn(
                "inline-block p-3 rounded-lg",
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-sm'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-sm'
              )}>
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                
                {/* Feature badges */}
                {msg.role === 'assistant' && msg.metadata?.feature && (
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-primary/10 text-primary">
                      {msg.metadata.feature === 'knowledge' && 'Knowledge'}
                      {msg.metadata.feature === 'quiz' && 'Quiz'}
                      {msg.metadata.feature === 'suggestions' && 'Suggestions'}
                      {msg.metadata.feature === 'learning_path' && 'Learning Path'}
                      {msg.metadata.feature === 'feedback' && 'Feedback'}
                    </span>
                    {typeof msg.metadata.confidence === 'number' && (
                      <span className="text-gray-500">Confidence: {(msg.metadata.confidence * 100).toFixed(0)}%</span>
                    )}
                    {typeof msg.metadata.tokens === 'number' && (
                      <span className="text-gray-500">Tokens: {msg.metadata.tokens}</span>
                    )}
                  </div>
                )}
                
                {/* AI Sources */}
                {msg.role === 'assistant' && msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Sources:</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.metadata.sources.map((source, index) => (
                        <span
                          key={index}
                          className="inline-block px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-300"
                        >
                          {source}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              <p className="text-xs text-gray-400 mt-1">
                {new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>
        ))}

        {/* Loading Message */}
        {sendMessageMutation.isPending && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg rounded-bl-sm">
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm text-gray-600 dark:text-gray-300">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about your learning journey..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
              rows={1}
              disabled={sendMessageMutation.isPending}
            />
          </div>
          {/* Dummy file upload button (UI only) */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFilesSelected}
            aria-label="Attach files"
          />
          <button
            type="button"
            onClick={handleFileButtonClick}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="Attach files (UI only)"
            aria-label="Attach files"
            disabled={sendMessageMutation.isPending}
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <button
            onClick={handleSendMessage}
            disabled={!message.trim() || sendMessageMutation.isPending}
            className="bg-primary text-white p-2 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        {attachedFiles.length > 0 && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
            <span className="inline-flex items-center gap-1">
              <Paperclip className="h-3 w-3" /> {attachedFiles.length} file{attachedFiles.length > 1 ? 's' : ''} selected
            </span>
            <span className="truncate">
              {attachedFiles.slice(0, 3).map(f => f.name).join(', ')}{attachedFiles.length > 3 ? '…' : ''}
            </span>
          </div>
        )}
        
        <p className="text-xs text-gray-400 mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

// Hook for easy integration
export function useAIChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(true);

  const openChat = () => {
    setIsOpen(true);
    setIsMinimized(false);
  };

  const closeChat = () => {
    setIsOpen(false);
    setIsMinimized(true);
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  return {
    isOpen,
    isMinimized,
    openChat,
    closeChat,
    toggleMinimize,
  };
} 