'use client';

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  FileText, 
  Download, 
  Eye, 
  Search, 
  Filter,
  Calendar,
  User,
  Building,
  ChevronDown,
  ExternalLink,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { KnowledgeDocument } from '@/types';
import { debounce } from '@/lib/utils';

interface DocumentViewerProps {
  className?: string;
}

// Transform backend response to match frontend types
interface BackendDocument {
  id: string;
  title: string;
  content: string;
  source_type: string;
  source_id?: string;
  org_id: string;
  metadata: Record<string, any>;
  embedding?: number[];
  created_at: string;
  updated_at: string;
}

function transformDocument(doc: BackendDocument): KnowledgeDocument {
  const result: KnowledgeDocument = {
    id: doc.id,
    title: doc.title,
    content: doc.content,
    sourceType: doc.source_type,
    orgId: doc.org_id,
    metadata: doc.metadata,
    createdAt: doc.created_at,
    updatedAt: doc.updated_at,
  };
  
  // Handle optional properties explicitly
  if (doc.source_id !== undefined) {
    result.sourceId = doc.source_id;
  }
  if (doc.embedding !== undefined) {
    result.embedding = doc.embedding;
  }
  
  return result;
}

export function DocumentViewer({ className }: DocumentViewerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  // Debounced search to avoid excessive API calls
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      setDebouncedQuery(query);
    }, 300),
    []
  );

  // Update debounced query when search query changes
  useEffect(() => {
    debouncedSearch(searchQuery);
  }, [searchQuery, debouncedSearch]);

  // Fetch documents with proper error handling
  const { data: documentsResponse, isLoading, error, refetch } = useQuery({
    queryKey: ['knowledge-documents', debouncedQuery, sourceFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (debouncedQuery) params.append('query', debouncedQuery);
      if (sourceFilter !== 'all') params.append('source_type', sourceFilter);
      params.append('limit', '50'); // Increased limit for better UX
      
      const response = await fetch(`/api/resources/knowledge-documents?${params}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: Failed to fetch documents`);
      }
      
      const data = await response.json();
      return data;
    },
    retry: 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Transform documents from backend format to frontend format
  const documents = useMemo(() => {
    if (!documentsResponse?.documents) return [];
    return documentsResponse.documents.map(transformDocument);
  }, [documentsResponse]);

  const sourceTypes = [
    { value: 'all', label: 'All Sources' },
    { value: 'upload', label: 'Uploaded Files' },
    { value: 'course', label: 'Course Materials' },
    { value: 'manual', label: 'Manual Entries' },
  ];

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'upload': return <FileText className="h-4 w-4 text-blue-500" />;
      case 'course': return <Building className="h-4 w-4 text-green-500" />;
      case 'manual': return <User className="h-4 w-4 text-purple-500" />;
      default: return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Invalid date';
    }
  };

  // Action handlers
  const handleViewDocument = useCallback((doc: KnowledgeDocument) => {
    // TODO: Implement document preview modal
    console.log('View document:', doc.title);
  }, []);

  const handleOpenDocument = useCallback((doc: KnowledgeDocument) => {
    // TODO: Open document in new tab
    console.log('Open document:', doc.title);
  }, []);

  const handleDownloadDocument = useCallback((doc: KnowledgeDocument) => {
    // TODO: Implement document download
    console.log('Download document:', doc.title);
  }, []);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  // Enhanced error state
  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="text-center py-12">
          <AlertCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400">Failed to load documents</h3>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">{error.message}</p>
          <button
            onClick={handleRetry}
            className="mt-4 inline-flex items-center space-x-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Try Again</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Knowledge Base</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Browse and search company documents and resources
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500" aria-live="polite">
              {isLoading ? 'Loading...' : `${documents.length} documents`}
            </span>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex items-center space-x-4 mt-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              aria-label="Search documents"
            />
          </div>
          
          <div className="relative">
            <button
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              aria-label="Filter documents by source type"
              aria-expanded={isFilterOpen}
              aria-haspopup="true"
            >
              <Filter className="h-4 w-4" />
              <span>{sourceTypes.find(s => s.value === sourceFilter)?.label}</span>
              <ChevronDown className="h-4 w-4" />
            </button>
            
            {isFilterOpen && (
              <div 
                className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10"
                role="menu"
                aria-label="Source type filter options"
              >
                {sourceTypes.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => {
                      setSourceFilter(type.value);
                      setIsFilterOpen(false);
                    }}
                    className={`w-full text-left px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors first:rounded-t-lg last:rounded-b-lg ${
                      sourceFilter === type.value ? 'bg-gray-50 dark:bg-gray-700' : ''
                    }`}
                    role="menuitem"
                    aria-selected={sourceFilter === type.value}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Documents List */}
      <div className="p-6">
        {isLoading ? (
          <div className="space-y-4" aria-label="Loading documents">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400">No documents found</h3>
            <p className="text-gray-500 mt-2">
              {searchQuery ? 'Try adjusting your search terms' : 'No documents have been uploaded yet'}
            </p>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="mt-3 text-sm text-primary hover:text-primary/80 transition-colors"
              >
                Clear search
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4" aria-label="Documents list">
            {documents.map((doc: KnowledgeDocument) => (
              <div
                key={doc.id}
                className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {getSourceIcon(doc.sourceType)}
                      <h3 className="font-medium text-gray-900 dark:text-white">{doc.title}</h3>
                    </div>
                    
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                      {doc.content}
                    </p>
                    
                    <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-3 w-3" />
                        <span>{formatDate(doc.createdAt)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Building className="h-3 w-3" />
                        <span className="capitalize">{doc.sourceType}</span>
                      </div>
                      {doc.metadata?.contentLength && (
                        <span>{Math.round(doc.metadata.contentLength / 1000)}k chars</span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => handleViewDocument(doc)}
                      className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      title="View document"
                      aria-label={`View document: ${doc.title}`}
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleOpenDocument(doc)}
                      className="p-2 text-gray-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
                      title="Open in new tab"
                      aria-label={`Open document in new tab: ${doc.title}`}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDownloadDocument(doc)}
                      className="p-2 text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                      title="Download document"
                      aria-label={`Download document: ${doc.title}`}
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
} 