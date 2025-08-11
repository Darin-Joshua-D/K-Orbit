"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth, useRole } from "@/lib/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { LogOut, Send, Users, BarChart3 } from "lucide-react";

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
  const [reportees, setReportees] = useState<{ users: any[]; total: number } | null>(null);

  // Dummy prototype data (UI only)
  const dummyMetrics = { totalUsers: 7, activeLearners: 7, engagementPct: 80 };
  const dummyTopPerformers: Array<{ id: string; full_name: string }> = [
    { id: "dj", full_name: "DJ" },
  ];
  const dummyTeamNames = [
    "DJ",
    "Mahendar",
    "Vivek",
    "Nayana",
    "Shoaib",
    "Harshitha",
    "Ashish",
  ];
  const dummyLearningBars = [8, 12, 6, 14, 10, 16, 9, 13, 11, 15, 7, 18];

  useEffect(() => {
    const fetchInsights = async () => {
      if (!hasAccess) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/analytics/organization-insights?period=${period}`);
        if (res.ok) {
          const data = await res.json();
          setInsights(data);
        } else {
          setInsights(null);
        }
      } catch {
        setInsights(null);
      } finally {
        setLoading(false);
      }
    };
    fetchInsights();
  }, [hasAccess, period]);

  useEffect(() => {
    const fetchReportees = async () => {
      if (!hasAccess) return;
      try {
        const res = await fetch('/api/users/reportees');
        if (res.ok) setReportees(await res.json());
        else setReportees(null);
      } catch {
        setReportees(null);
      }
    };
    fetchReportees();
  }, [hasAccess]);

  const engagementPct = useMemo(() => {
    if (insights) return Math.round((insights.overview.engagement_rate || 0) * 100);
    if (!loading) return dummyMetrics.engagementPct;
    return 0;
  }, [insights, loading]);

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

  // Decide whether to show dummy or API values
  const totalUsersDisplay = insights?.overview.total_users ?? (!loading ? dummyMetrics.totalUsers : '…');
  const activeLearnersDisplay = insights?.overview.active_learners ?? (!loading ? dummyMetrics.activeLearners : '…');

  const usingDummyTopPerformers = !loading && (!insights || !insights.top_performers || insights.top_performers.length === 0);
  const topPerformersDisplay = usingDummyTopPerformers ? dummyTopPerformers : (insights?.top_performers || []);

  const usingDummyTeam = !reportees || !reportees.users || reportees.users.length === 0;
  const teamCountLabel = usingDummyTeam ? `${dummyTeamNames.length} members` : `${reportees?.total ?? 0} members`;
  const teamList = usingDummyTeam ? dummyTeamNames : reportees!.users.map((u: any) => u.full_name);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <header className="space-y-1">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Manager Dashboard</h1>
              <p className="text-gray-600 dark:text-gray-400">Welcome{user?.email ? `, ${user.email}` : ""}</p>
            </div>
            <Button variant="outline" onClick={signOut} className="gap-2">
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </header>

        {/* Org overview cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6">
            <p className="text-sm text-muted-foreground">Total users</p>
            <p className="text-2xl font-semibold">{totalUsersDisplay}</p>
          </div>
          <div className="glass-card p-6">
            <p className="text-sm text-muted-foreground">Active learners ({period})</p>
            <p className="text-2xl font-semibold">{activeLearnersDisplay}</p>
          </div>
          <div className="glass-card p-6">
            <p className="text-sm text-muted-foreground">Engagement</p>
            <p className="text-2xl font-semibold">{loading ? '…' : `${engagementPct}%`}</p>
          </div>
        </div>

        {/* Colored graph of learnings (dummy UI) */}
        <div className="glass p-6 rounded-xl">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2"><BarChart3 className="h-4 w-4" /> Learnings</h2>
            <span className="text-sm text-gray-500">Last 30 days</span>
          </div>
          <div className="h-32 flex items-end gap-2">
            {(insights ? insights.course_performance?.slice(0, 12).map((_: any, i: number) => i + 8) : dummyLearningBars).map((v: number, idx: number) => (
              <div
                key={idx}
                className="flex-1 rounded-t-md"
                style={{
                  height: `${Math.max(6, Math.min(18, v)) * 6}px`,
                  background: `linear-gradient(180deg, rgba(59,130,246,0.9), rgba(99,102,241,0.8))`,
                  boxShadow: '0 2px 8px rgba(59,130,246,0.25)'
                }}
                aria-label={`Day ${idx + 1} value ${v}`}
                title={`Day ${idx + 1}: ${v}`}
              />
            ))}
          </div>
        </div>

        {/* Top performers */}
        <div className="glass p-6 rounded-xl">
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
              {topPerformersDisplay.map(tp => (
                <li key={tp.id} className="flex items-center justify-between">
                  <span>{tp.full_name}</span>
                </li>
              ))}
              {topPerformersDisplay.length === 0 && (
                <p className="text-sm text-muted-foreground">No data</p>
              )}
            </ul>
          )}
        </div>

        {/* Reportees overview */}
        <div className="glass p-6 rounded-xl">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2"><Users className="h-4 w-4" /> Your team</h2>
            <span className="text-sm text-gray-500">{teamCountLabel}</span>
          </div>
          {usingDummyTeam ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {dummyTeamNames.map((name) => (
                <div key={name} className="flex items-center justify-between p-3 bg-white/60 dark:bg-gray-800/60 rounded-lg">
                  <div>
                    <p className="font-medium">{name}</p>
                    <p className="text-xs text-gray-500">example@company.com</p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700">member</span>
                </div>
              ))}
            </div>
          ) : (
            reportees?.users?.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {reportees.users.slice(0, 6).map((u: any) => (
                  <div key={u.id} className="flex items-center justify-between p-3 bg-white/60 dark:bg-gray-800/60 rounded-lg">
                    <div>
                      <p className="font-medium">{u.full_name}</p>
                      <p className="text-xs text-gray-500">{u.email}</p>
                    </div>
                    <span className="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700">{u.role}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No team members found</p>
            )
          )}
        </div>

        {/* Announcements */}
        <div className="glass p-6 rounded-xl space-y-3">
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
        </div>
      </div>
    </div>
  );
} 