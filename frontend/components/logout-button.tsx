"use client";
import { useAuth } from '@/lib/auth/auth-provider';
import { useRouter } from 'next/navigation';

export function LogoutButton({ className = '' }: { className?: string }) {
  const { signOut } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await signOut();
    router.refresh();
  };

  return (
    <button
      onClick={handleLogout}
      className={`btn-ghost text-sm ${className}`}
    >
      Logout
    </button>
  );
} 