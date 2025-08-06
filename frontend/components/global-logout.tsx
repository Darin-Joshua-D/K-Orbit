"use client";
import { LogoutButton } from './logout-button';
import { useAuth } from '@/lib/auth/auth-provider';

export function GlobalLogout() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <div className="fixed top-4 right-4 z-50">
      <LogoutButton />
    </div>
  );
} 