'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, useRole } from '@/lib/auth/auth-provider';
import { Loader2 } from 'lucide-react';

export default function DashboardRouter() {
  const { user, loading } = useAuth();
  const { role } = useRole();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      // Redirect based on user role
      switch (role) {
        case 'admin':
        case 'super_admin':
          router.push('/dashboard/admin');
          break;
        case 'manager':
          router.push('/dashboard/manager');
          break;
        case 'sme':
          router.push('/dashboard/sme');
          break;
        case 'learner':
        default:
          router.push('/dashboard/learner');
          break;
      }
    } else if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, role, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">Redirecting to your dashboard...</p>
      </div>
    </div>
  );
} 