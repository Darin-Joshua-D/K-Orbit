'use client';

import React, { useState } from 'react';
import { useAuth } from '@/lib/auth/auth-provider';
import { withAuth } from '@/lib/auth/auth-provider';

import { 
  BookOpen, 
  Trophy, 
  Target,
  Clock,
  Star,
  TrendingUp,
  MessageCircle,
  Award,
  Play,
  CheckCircle,
  Bot
} from 'lucide-react';

function LearnerDashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');

  // Mock data - in real app, this would come from API
  const mockData = {
    userStats: {
      totalXP: 2450,
      level: 7,
      levelProgress: 65,
      coursesCompleted: 12,
      coursesInProgress: 3,
      badgesEarned: 8,
      streakDays: 14,
      rank: 23,
      totalUsers: 156
    },
    recommendedCourses: [
      {
        id: '1',
        title: 'Advanced React Patterns',
        description: 'Master advanced React concepts and patterns',
        thumbnail: '/api/placeholder/300/200',
        difficulty: 'Advanced',
        duration: '6 hours',
        rating: 4.8,
        enrolledCount: 234,
        tags: ['React', 'JavaScript', 'Frontend']
      },
      {
        id: '2',
        title: 'Cloud Architecture Fundamentals',
        description: 'Learn cloud computing principles and AWS basics',
        thumbnail: '/api/placeholder/300/200',
        difficulty: 'Intermediate',
        duration: '8 hours',
        rating: 4.9,
        enrolledCount: 189,
        tags: ['AWS', 'Cloud', 'Architecture']
      }
    ],
    currentCourses: [
      {
        id: '3',
        title: 'TypeScript Deep Dive',
        progress: 75,
        totalLessons: 20,
        completedLessons: 15,
        lastAccessed: '2024-01-15T10:30:00Z',
        nextLesson: 'Generic Constraints'
      },
      {
        id: '4',
        title: 'API Design Best Practices',
        progress: 40,
        totalLessons: 16,
        completedLessons: 6,
        lastAccessed: '2024-01-14T14:20:00Z',
        nextLesson: 'RESTful Principles'
      }
    ],
    recentBadges: [
      {
        id: '1',
        name: 'Quick Learner',
        description: 'Completed 3 lessons in one day',
        iconUrl: '🚀',
        earnedAt: '2024-01-15T09:00:00Z'
      },
      {
        id: '2',
        name: 'Consistent Student',
        description: '7-day learning streak',
        iconUrl: '🔥',
        earnedAt: '2024-01-14T18:00:00Z'
      }
    ],
    upcomingDeadlines: [
      {
        id: '1',
        title: 'Complete Security Training',
        dueDate: '2024-01-20T23:59:59Z',
        type: 'mandatory',
        progress: 80
      }
    ]
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Target },
    { id: 'courses', label: 'My Courses', icon: BookOpen },
    { id: 'achievements', label: 'Achievements', icon: Trophy },
    { id: 'forum', label: 'Forum', icon: MessageCircle }
  ];

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="glass-card p-6 hover:scale-105 transition-transform duration-300">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total XP</p>
              <p className="text-2xl font-bold text-primary">{mockData.userStats.totalXP}</p>
            </div>
            <Trophy className="h-8 w-8 text-primary/60" />
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">Level {mockData.userStats.level} • {mockData.userStats.levelProgress}% to next</p>
          </div>
        </div>

        <div className="glass-card p-6 hover:scale-105 transition-transform duration-300">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Courses</p>
              <p className="text-2xl font-bold">{mockData.userStats.coursesCompleted}</p>
            </div>
            <BookOpen className="h-8 w-8 text-blue-500/60" />
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">{mockData.userStats.coursesInProgress} in progress</p>
          </div>
        </div>

        <div className="glass p-6 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Streak</p>
              <p className="text-2xl font-bold text-orange-500">{mockData.userStats.streakDays} days</p>
            </div>
            <div className="text-2xl">🔥</div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">Keep it up!</p>
          </div>
        </div>

        <div className="glass p-6 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Rank</p>
              <p className="text-2xl font-bold text-green-500">#{mockData.userStats.rank}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-500/60" />
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">of {mockData.userStats.totalUsers} learners</p>
          </div>
        </div>
      </div>

      {/* Current Courses */}
      <div className="glass p-6 rounded-xl">
        <h2 className="text-xl font-semibold mb-4">Continue Learning</h2>
        <div className="space-y-4">
          {mockData.currentCourses.map((course) => (
            <div key={course.id} className="flex items-center space-x-4 p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-gradient-to-br from-primary to-blue-600 rounded-lg flex items-center justify-center">
                  <Play className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="flex-grow">
                <h3 className="font-semibold">{course.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Next: {course.nextLesson} • {course.completedLessons}/{course.totalLessons} lessons
                </p>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-primary rounded-full h-2 transition-all duration-300"
                      style={{ width: `${course.progress}%` }}
                    />
                  </div>
                </div>
              </div>
              <button className="btn-primary">Continue</button>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Achievements */}
      <div className="glass p-6 rounded-xl">
        <h2 className="text-xl font-semibold mb-4">Recent Achievements</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mockData.recentBadges.map((badge) => (
            <div key={badge.id} className="flex items-center space-x-3 p-3 bg-white/50 dark:bg-gray-800/50 rounded-lg">
              <div className="text-2xl">{badge.iconUrl}</div>
              <div>
                <h4 className="font-semibold">{badge.name}</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">{badge.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended Courses */}
      <div className="glass p-6 rounded-xl">
        <h2 className="text-xl font-semibold mb-4">Recommended for You</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {mockData.recommendedCourses.map((course) => (
            <div key={course.id} className="course-card">
              <div className="h-32 bg-gradient-to-br from-primary/20 to-blue-600/20 rounded-t-lg flex items-center justify-center">
                <BookOpen className="h-12 w-12 text-primary" />
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="badge badge-primary">{course.difficulty}</span>
                  <div className="flex items-center">
                    <Star className="h-4 w-4 text-yellow-500 mr-1" />
                    <span className="text-sm">{course.rating}</span>
                  </div>
                </div>
                <h3 className="font-semibold mb-2">{course.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{course.description}</p>
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span className="flex items-center">
                    <Clock className="h-4 w-4 mr-1" />
                    {course.duration}
                  </span>
                  <span>{course.enrolledCount} enrolled</span>
                </div>
                <button className="btn-primary w-full mt-4">Enroll Now</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderCourses = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">My Courses</h1>
        <button className="btn-primary">Browse All Courses</button>
      </div>
      
      {/* Course filters and list would go here */}
      <div className="glass p-6 rounded-xl">
        <p className="text-gray-600 dark:text-gray-400">Course management interface would be implemented here.</p>
      </div>
    </div>
  );

  const renderAchievements = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">My Achievements</h1>
        <div className="flex items-center space-x-2">
          <Trophy className="h-5 w-5 text-primary" />
          <span className="font-semibold">{mockData.userStats.badgesEarned} badges earned</span>
        </div>
      </div>
      
      {/* Achievements grid would go here */}
      <div className="glass p-6 rounded-xl">
        <p className="text-gray-600 dark:text-gray-400">Achievement and badge system would be implemented here.</p>
      </div>
    </div>
  );

  const renderForum = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Community Forum</h1>
        <button className="btn-primary">Ask Question</button>
      </div>
      
      {/* Forum interface would go here */}
      <div className="glass p-6 rounded-xl">
        <p className="text-gray-600 dark:text-gray-400">Forum interface would be implemented here.</p>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return renderOverview();
      case 'courses':
        return renderCourses();
      case 'achievements':
        return renderAchievements();
      case 'forum':
        return renderForum();
      default:
        return renderOverview();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Welcome back, {user?.user_metadata?.full_name || 'Learner'}! 👋
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Ready to continue your learning journey?
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="level-ring">
                <span className="text-sm font-bold">{mockData.userStats.level}</span>
              </div>
              <div className="xp-badge">
                {mockData.userStats.totalXP} XP
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex space-x-1 mb-8">
          {tabs.map((tab) => {
            const IconComponent = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                <IconComponent className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Main Content */}
        {renderContent()}
      </div>


    </div>
  );
}

export default withAuth(LearnerDashboard); 