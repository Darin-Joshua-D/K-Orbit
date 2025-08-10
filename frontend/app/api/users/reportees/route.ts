import { NextRequest, NextResponse } from 'next/server';
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  try {
    const supabase = createRouteHandlerClient({ cookies });
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error || !session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    // First get current user to know their id
    const meResp = await fetch(`${backendUrl}/api/auth/profile`, {
      headers: { Authorization: `Bearer ${session.access_token}` }
    });
    if (!meResp.ok) return NextResponse.json({ error: 'Failed to get profile' }, { status: 500 });
    const me = await meResp.json();

    const url = new URL(request.url);
    const page = url.searchParams.get('page') || '1';
    const limit = url.searchParams.get('limit') || '20';

    const resp = await fetch(`${backendUrl}/api/users/search?manager_id=${me.id}&page=${page}&limit=${limit}`, {
      headers: { Authorization: `Bearer ${session.access_token}` }
    });

    if (!resp.ok) {
      const text = await resp.text();
      console.error('Backend reportees error:', resp.status, text);
      return NextResponse.json({ error: 'Failed to fetch reportees' }, { status: 500 });
    }

    const data = await resp.json();
    return NextResponse.json(data);
  } catch (e) {
    console.error('Reportees API error:', e);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 