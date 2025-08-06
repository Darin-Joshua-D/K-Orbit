import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('query') || '';
    const sourceType = searchParams.get('source_type') || '';
    const limit = searchParams.get('limit') || '10';
    const offset = searchParams.get('offset') || '0';

    // Build backend URL with query parameters
    const backendParams = new URLSearchParams();
    if (query) backendParams.append('query', query);
    if (sourceType) backendParams.append('source_type', sourceType);
    backendParams.append('limit', limit);
    backendParams.append('offset', offset);

    const backendUrl = `${BACKEND_URL}/api/resources/knowledge-documents?${backendParams.toString()}`;

    // Forward request to backend with authentication
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('Authorization') || '',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend request failed: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('API route error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch documents' },
      { status: 500 }
    );
  }
} 