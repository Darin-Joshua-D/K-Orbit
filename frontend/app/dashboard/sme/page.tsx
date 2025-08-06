'use client';

import React, { useState } from 'react';
import { useAuth } from '@/lib/auth/auth-provider';
import { withAuth } from '@/lib/auth/auth-provider';
import { 
  Upload, 
  FileText, 
  Users,
  BarChart3,
  BookOpen,
  Plus,
  Search,
  Filter,
  Download,
  Eye,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  LogOut
} from 'lucide-react';

function SMEDashboard() {
  const { user, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [searchQuery, setSearchQuery] = useState('');

  // Mock data - in real app, this would come from API
  const mockData = {
    stats: {
      documentsUploaded: 45,
      studentsHelped: 234,
      averageRating: 4.8,
      coursesContributed: 12
    },
    recentDocuments: [
      {
        id: '1',
        title: 'React Best Practices Guide',
        type: 'PDF',
        size: '2.4 MB',
        uploadedAt: '2024-01-15T10:30:00Z',
        status: 'processed',
        views: 156,
        downloads: 89
      },
      {
        id: '2',
        title: 'API Documentation Template',
        type: 'DOCX',
        size: '1.2 MB',
        uploadedAt: '2024-01-14T15:45:00Z',
        status: 'processing',
        views: 0,
        downloads: 0
      },
      {
        id: '3',
        title: 'Database Design Patterns',
        type: 'PDF',
        size: '3.1 MB',
        uploadedAt: '2024-01-13T09:15:00Z',
        status: 'processed',
        views: 201,
        downloads: 145
      }
    ],
    analytics: {
      documentsThisMonth: 8,
      totalViews: 1240,
      totalDownloads: 567,
      mostPopular: 'JavaScript Advanced Concepts'
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'courses', label: 'Courses', icon: BookOpen },
    { id: 'students', label: 'Students', icon: Users }
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing': return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'error': return <AlertCircle className="h-4 w-4 text-red-500" />;
      default: return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Documents</p>
              <p className="text-2xl font-bold">{mockData.stats.documentsUploaded}</p>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Students Helped</p>
              <p className="text-2xl font-bold">{mockData.stats.studentsHelped}</p>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <Users className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Average Rating</p>
              <p className="text-2xl font-bold">{mockData.stats.averageRating}</p>
            </div>
            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              <BarChart3 className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Courses</p>
              <p className="text-2xl font-bold">{mockData.stats.coursesContributed}</p>
            </div>
            <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <BookOpen className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4">Recent Document Activity</h3>
        <div className="space-y-4">
          {mockData.recentDocuments.slice(0, 3).map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="flex items-center space-x-3">
                {getStatusIcon(doc.status)}
                <div>
                  <p className="font-medium">{doc.title}</p>
                  <p className="text-sm text-gray-500">{new Date(doc.uploadedAt).toLocaleDateString()}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">{doc.views} views</p>
                <p className="text-sm text-gray-500">{doc.downloads} downloads</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderDocuments = () => (
    <div className="space-y-6">
      {/* Upload Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Upload New Document</h3>
          <button className="btn-primary flex items-center space-x-2">
            <Upload className="h-4 w-4" />
            <span>Upload Files</span>
          </button>
        </div>
        
        <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
          <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-600 dark:text-gray-400">
            Drag and drop files here, or click to browse
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Supports PDF, DOC, DOCX, TXT, MD files up to 50MB
          </p>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-4 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>
          <button className="btn-secondary flex items-center space-x-2">
            <Filter className="h-4 w-4" />
            <span>Filter</span>
          </button>
        </div>

        {/* Documents List */}
        <div className="space-y-3">
          {mockData.recentDocuments.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
              <div className="flex items-center space-x-4">
                {getStatusIcon(doc.status)}
                <div className="flex-1">
                  <h4 className="font-medium">{doc.title}</h4>
                  <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                    <span>{doc.type}</span>
                    <span>{doc.size}</span>
                    <span>{new Date(doc.uploadedAt).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <div className="text-right text-sm mr-4">
                  <p className="font-medium">{doc.views} views</p>
                  <p className="text-gray-500">{doc.downloads} downloads</p>
                </div>
                
                <button className="p-2 text-gray-400 hover:text-blue-600 transition-colors">
                  <Eye className="h-4 w-4" />
                </button>
                <button className="p-2 text-gray-400 hover:text-green-600 transition-colors">
                  <Download className="h-4 w-4" />
                </button>
                <button className="p-2 text-gray-400 hover:text-yellow-600 transition-colors">
                  <Edit className="h-4 w-4" />
                </button>
                <button className="p-2 text-gray-400 hover:text-red-600 transition-colors">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'overview': return renderOverview();
      case 'documents': return renderDocuments();
      case 'courses': 
        return (
          <div className="text-center py-12">
            <BookOpen className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400">Course Management</h3>
            <p className="text-gray-500 mt-2">Create and manage learning courses for your organization</p>
          </div>
        );
      case 'students':
        return (
          <div className="text-center py-12">
            <Users className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400">Student Analytics</h3>
            <p className="text-gray-500 mt-2">View student progress and engagement metrics</p>
          </div>
        );
      default: return renderOverview();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">SME Dashboard</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Welcome back, {user?.user_metadata?.full_name || 'SME'}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <button className="btn-primary flex items-center space-x-2">
                <Plus className="h-4 w-4" />
                <span>Create New</span>
              </button>
              <button
                onClick={() => signOut()}
                className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="flex space-x-1 mb-8 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-fit">
          {tabs.map((tab) => {
            const IconComponent = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
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

export default withAuth(SMEDashboard, { requiredRole: 'sme' }); 