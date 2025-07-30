/**
 * Core type definitions for K-Orbit application
 */

import { ReactNode } from 'react';

// User and Authentication Types
export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  orgId: string;
  avatarUrl?: string;
  department?: string;
  position?: string;
  managerId?: string;
  onboardingCompleted: boolean;
  lastActive?: Date;
  createdAt: Date;
  updatedAt?: Date;
}

export type UserRole = 'learner' | 'sme' | 'manager' | 'admin' | 'super_admin';

export interface AuthSession {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresAt: Date;
}

// Course and Learning Types
export interface Course {
  id: string;
  title: string;
  description: string;
  category: string;
  difficultyLevel: 'beginner' | 'intermediate' | 'advanced';
  estimatedDuration: number; // in minutes
  tags: string[];
  prerequisites: string[];
  learningObjectives: string[];
  isMandatory: boolean;
  autoEnrollRoles: UserRole[];
  status: 'draft' | 'published' | 'archived';
  authorId: string;
  authorName: string;
  thumbnailUrl?: string;
  totalLessons: number;
  totalEnrollments: number;
  avgRating?: number;
  createdAt: Date;
  updatedAt?: Date;
  publishedAt?: Date;
}

export interface Lesson {
  id: string;
  courseId: string;
  title: string;
  content: string;
  lessonType: 'video' | 'reading' | 'quiz' | 'interactive' | 'assignment';
  orderIndex: number;
  duration: number; // in minutes
  isRequired: boolean;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt?: Date;
}

export interface Enrollment {
  id: string;
  courseId: string;
  userId: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'paused';
  progressPercentage: number;
  currentLessonId?: string;
  completedLessons: string[];
  timeSpent: number; // in minutes
  startedAt?: Date;
  completedAt?: Date;
  lastAccessed?: Date;
  createdAt: Date;
}

export interface LessonProgress {
  lessonId: string;
  userId: string;
  status: 'not_started' | 'in_progress' | 'completed';
  progressPercentage: number;
  timeSpent: number; // in minutes
  completedAt?: Date;
  lastAccessed?: Date;
}

// Document and Knowledge Management Types
export interface KnowledgeDocument {
  id: string;
  title: string;
  content: string;
  sourceType: string;
  sourceId?: string;
  orgId: string;
  metadata: Record<string, any>;
  embedding?: number[];
  createdAt: string;
  updatedAt: string;
}

export interface FileUploadResponse {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  url: string;
  isProcessed: boolean;
  uploadedAt: string;
}

export interface DocumentProcessingResponse {
  success: boolean;
  message: string;
  fileId?: string;
  extractedText?: string;
  hasEmbedding?: boolean;
}

export interface DocumentSearchRequest {
  query?: string;
  sourceType?: string;
  limit?: number;
  offset?: number;
}

export interface DocumentSearchResponse {
  documents: KnowledgeDocument[];
  total: number;
  query?: string;
  searchType: 'semantic' | 'text' | 'recent';
}

// Gamification Types
export interface XPTransaction {
  id: string;
  userId: string;
  xpEarned: number;
  source: string; // 'course_completion', 'lesson_completion', 'forum_answer', etc.
  sourceId?: string;
  description: string;
  createdAt: Date;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  iconUrl: string;
  criteria: BadgeCriteria;
  xpReward: number;
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  createdAt: Date;
}

export interface BadgeCriteria {
  type: 'course_completion' | 'xp_milestone' | 'streak' | 'forum_contribution' | 'custom';
  target: number;
  conditions?: Record<string, any>;
}

export interface UserBadge {
  id: string;
  userId: string;
  badgeId: string;
  badge: Badge;
  earnedAt: Date;
}

export interface UserStats {
  userId: string;
  totalXp: number;
  level: number;
  levelProgress: number; // 0-1
  badgesEarned: number;
  coursesCompleted: number;
  coursesInProgress: number;
  forumPosts: number;
  forumHelpfulAnswers: number;
  loginStreak: number;
  lastActivity?: Date;
}

// Forum Types
export interface ForumQuestion {
  id: string;
  title: string;
  content: string;
  tags: string[];
  userId: string;
  userName: string;
  userAvatar?: string;
  courseId?: string;
  isResolved: boolean;
  viewCount: number;
  upvotes: number;
  downvotes: number;
  createdAt: Date;
  updatedAt?: Date;
}

export interface ForumAnswer {
  id: string;
  questionId: string;
  content: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  isHelpful: boolean;
  isAccepted: boolean;
  upvotes: number;
  downvotes: number;
  createdAt: Date;
  updatedAt?: Date;
}

// AI Chat Types
export interface ChatMessage {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    sources?: string[];
    confidence?: number;
    tokens?: number;
  };
  createdAt: Date;
}

export interface ChatConversation {
  id: string;
  userId: string;
  title: string;
  summary?: string;
  messageCount: number;
  lastMessageAt: Date;
  createdAt: Date;
}

export interface ChatRequest {
  message: string;
  conversationId?: string;
}

export interface ChatResponse {
  message: ChatMessage;
  conversationId: string;
  sources?: KnowledgeDocument[];
}

// Analytics Types
export interface AnalyticsMetric {
  name: string;
  value: number;
  change?: number; // percentage change
  period: 'day' | 'week' | 'month' | 'quarter' | 'year';
  timestamp: Date;
}

export interface ProgressMetrics {
  totalCourses: number;
  completedCourses: number;
  completionRate: number;
  totalXpEarned: number;
  averageProgress: number;
}

export interface EngagementMetrics {
  dailyActiveUsers: number;
  weeklyActiveUsers: number;
  monthlyActiveUsers: number;
  avgSessionDuration: number;
  userRetentionRate: number;
}

export interface LearningPath {
  id: string;
  name: string;
  description: string;
  courses: Course[];
  estimatedDuration: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  completionRate: number;
  enrolledUsers: number;
}

// Notification Types
export interface Notification {
  id: string;
  userId: string;
  type: 'xp_earned' | 'badge_earned' | 'course_assigned' | 'forum_answer' | 'system';
  title: string;
  message: string;
  isRead: boolean;
  actionUrl?: string;
  metadata?: Record<string, any>;
  createdAt: Date;
}

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

export interface RealTimeEvent {
  type: 'xp_earned' | 'badge_earned' | 'course_completed' | 'forum_notification' | 'system_alert';
  data: any;
  userId?: string;
  room?: string;
}

// API Response Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T = any> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// Search and Filter Types
export interface SearchParams {
  query?: string;
  filters?: Record<string, any>;
  sort?: {
    field: string;
    order: 'asc' | 'desc';
  };
  page?: number;
  limit?: number;
}

// Dashboard Types
export interface DashboardData {
  user: User;
  stats: UserStats;
  recentActivity: any[];
  recommendations: Course[];
  notifications: Notification[];
  upcomingDeadlines: any[];
}

// File Upload Types
export interface FileUpload {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  size: number;
  url: string;
  uploadedBy: string;
  createdAt: Date;
}

// Organization Types
export interface Organization {
  id: string;
  name: string;
  slug: string;
  domain: string;
  settings: OrganizationSettings;
  createdAt: Date;
  updatedAt?: Date;
}

export interface OrganizationSettings {
  branding: {
    logo?: string;
    primaryColor: string;
    secondaryColor: string;
  };
  features: {
    gamificationEnabled: boolean;
    forumEnabled: boolean;
    aiChatEnabled: boolean;
    analyticsEnabled: boolean;
  };
  policies: {
    passwordPolicy: Record<string, any>;
    sessionTimeout: number;
    maxFileSize: number;
  };
}

// Component Props Types
export interface BaseProps {
  className?: string;
  children?: ReactNode;
}

export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

// Form Types
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'select' | 'textarea' | 'file' | 'checkbox';
  required?: boolean;
  placeholder?: string;
  options?: { label: string; value: string }[];
  validation?: Record<string, any>;
}

// Theme Types
export type Theme = 'light' | 'dark' | 'system';

// Export utility types
export type Prettify<T> = {
  [K in keyof T]: T[K];
} & {};

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type RequiredBy<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
}; 