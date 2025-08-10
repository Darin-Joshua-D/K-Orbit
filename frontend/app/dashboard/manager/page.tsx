"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth, useRole } from "@/lib/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { LogOut, Send } from "lucide-react";

interface OrgInsights {
  organization_id: string;
  period: string;
  overview: { total_users: number; active_learners: number; engagement_rate: number };
  course_performance: any[];
  top_performers: Array<{ id: string; full_name: string }>;
}

export default function ManagerDashboardPage() {
  const { user, signOut } = useAuth();
  const { role } = useRole();

  const hasAccess = role === "manager" || role === "admin" || role === "super_admin";

  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("30d");
  const [insights, setInsights] = useState<OrgInsights | null>(null);
  const [announceMsg, setAnnounceMsg] = useState("");
  const [announceRole, setAnnounceRole] = useState("learner");
  const [announceSending, setAnnounceSending] = useState(false);

  useEffect(() => {
    const fetchInsights = async () => {
      if (!hasAccess) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/analytics/organization-insights?period=${period}`);
        if (res.ok) {
          const data = await res.json();
          setInsights(data);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchInsights();
  }, [hasAccess, period]);

  const engagementPct = useMemo(() => {
    if (!insights) return 0;
    return Math.round((insights.overview.engagement_rate || 0) * 100);
  }, [insights]);

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

  const sendAnnouncement = async () => {
    if (!announceMsg.trim()) return;
    setAnnounceSending(true);
    try {
      const resp = await fetch('/api/realtime/announcement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: announceMsg.trim(), target_role: announceRole, priority: 'normal' })
      });
      if (resp.ok) {
        setAnnounceMsg("");
      }
    } finally {
      setAnnounceSending(false);
    }
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="space-y-1">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Manager Dashboard</h1>
              <p className="text-muted-foreground">Welcome{user?.email ? `, ${user.email}` : ""}</p>
            </div>
            <Button variant="outline" onClick={signOut} className="gap-2">
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </header>

        {/* Org overview cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <p className="text-sm text-muted-foreground">Total users</p>
            <p className="text-2xl font-semibold">{insights?.overview.total_users ?? (loading ? '…' : 0)}</p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-muted-foreground">Active learners ({period})</p>
            <p className="text-2xl font-semibold">{insights?.overview.active_learners ?? (loading ? '…' : 0)}</p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-muted-foreground">Engagement</p>
            <p className="text-2xl font-semibold">{loading ? '…' : `${engagementPct}%`}</p>
          </Card>
        </div>

        {/* Top performers */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Top performers</h2>
            <select value={period} onChange={(e) => setPeriod(e.target.value)} className="border rounded px-2 py-1 text-sm">
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (
            <ul className="space-y-2">
              {(insights?.top_performers || []).slice(0, 10).map(tp => (
                <li key={tp.id} className="flex items-center justify-between">
                  <span>{tp.full_name}</span>
                </li>
              ))}
              {(!insights?.top_performers || insights.top_performers.length === 0) && (
                <p className="text-sm text-muted-foreground">No data</p>
              )}
            </ul>
          )}
        </Card>

        {/* Announcements */}
        <Card className="p-4 space-y-3">
          <h2 className="font-semibold">Send announcement</h2>
          <div className="grid gap-2 md:grid-cols-[1fr,160px] items-start">
            <Textarea value={announceMsg} onChange={(e) => setAnnounceMsg(e.target.value)} placeholder="Write a short message…" />
            <div className="flex items-center gap-2">
              <select value={announceRole} onChange={(e) => setAnnounceRole(e.target.value)} className="border rounded px-2 py-2 text-sm">
                <option value="learner">Learners</option>
                <option value="sme">SMEs</option>
                <option value="manager">Managers</option>
              </select>
              <Button onClick={sendAnnouncement} disabled={announceSending || !announceMsg.trim()} className="gap-2">
                <Send className="h-4 w-4" />
                Send
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
} 