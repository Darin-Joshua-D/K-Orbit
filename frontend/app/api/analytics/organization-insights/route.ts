import { NextRequest, NextResponse } from 'next/server';
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  try {
    const supabase = createRouteHandlerClient({ cookies });
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();

    if (sessionError || !session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const period = searchParams.get('period') || '30d';

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const resp = await fetch(`${backendUrl}/api/analytics/organization-insights?period=${encodeURIComponent(period)}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
      },
    });

    if (!resp.ok) {
      const text = await resp.text();
      console.error('Backend API error (organization-insights):', resp.status, text);
      return NextResponse.json({ error: 'Failed to fetch organization insights' }, { status: resp.status });
    }

    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Organization insights API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 