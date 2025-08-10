"use client";

import React from "react";
import Link from "next/link";
import { useAuth, useRole } from "@/lib/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";

export default function ManagerDashboardPage() {
  const { user, signOut } = useAuth();
  const { role } = useRole();

  const hasAccess = role === "manager" || role === "admin" || role === "super_admin";

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-3">
          <p className="text-xl font-semibold">You are not signed in</p>
          <Link href="/auth/login" className="underline text-primary">Sign in</Link>
        </div>
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-3">
          <p className="text-xl font-semibold">Access denied</p>
          <p className="text-muted-foreground">This area is for managers/admins.</p>
          <Link href="/dashboard" className="underline text-primary">Go to your dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="space-y-1">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Manager Dashboard</h1>
              <p className="text-muted-foreground">Welcome{user?.email ? `, ${user.email}` : ""}. This is a minimal manager view. We can expand this with reports, team progress, approvals, etc.</p>
            </div>
            <Button variant="outline" onClick={signOut} className="gap-2">
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </header>

        <div className="rounded-lg border bg-card p-6">
          <p className="text-sm text-muted-foreground">
            This page is a placeholder so the route exists. If you want specific manager widgets (team course progress, approvals, announcements), tell me and I’ll wire them up.
          </p>
        </div>
      </div>
    </div>
  );
} 