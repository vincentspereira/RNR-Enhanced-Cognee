/**
 * Next.js API Route for Real-Time Enhanced Cognee Features
 * Provides SSE endpoints for live updates and WebSocket connection management
 */

import { NextRequest, NextResponse } from 'next/server';

// WebSocket server URL (configured via environment)
const WS_SERVER_URL = process.env.WS_SERVER_URL || 'ws://localhost:8765';

/**
 * GET /api/realtime/events
 * Server-Sent Events endpoint for real-time updates
 */
export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const eventType = url.searchParams.get('event') || 'all';

  // Create SSE stream
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Send SSE headers
      const sendEvent = (data: any) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      };

      // Send initial connection message
      sendEvent({
        type: 'connected',
        message: 'Connected to Enhanced Cognee Real-Time Updates',
        timestamp: new Date().toISOString(),
        subscribedTo: eventType
      });

      // Simulate real-time updates (in production, connect to WebSocket server)
      const interval = setInterval(async () => {
        try {
          // Here you would connect to the Python WebSocket server
          // For now, sending heartbeat
          sendEvent({
            type: 'heartbeat',
            timestamp: new Date().toISOString()
          });
        } catch (error) {
          console.error('SSE error:', error);
          clearInterval(interval);
          controller.close();
        }
      }, 30000); // Heartbeat every 30 seconds

      // Cleanup on connection close
      request.signal.addEventListener('abort', () => {
        clearInterval(interval);
        controller.close();
      });
    },
  });

  return new NextResponse(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * POST /api/realtime/notify
 * Send notification to WebSocket server
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { event, data } = body;

    // Forward to WebSocket server
    const response = await fetch(`${WS_SERVER_URL}/api/notify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, data }),
    });

    if (response.ok) {
      return NextResponse.json({ success: true, message: 'Notification sent' });
    } else {
      return NextResponse.json(
        { success: false, error: 'Failed to send notification' },
        { status: response.status }
      );
    }
  } catch (error) {
    console.error('Notify error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * GET /api/realtime/stats
 * Get WebSocket server statistics
 */
export async function GET_STATS(request: NextRequest) {
  try {
    // Query WebSocket server for stats
    const response = await fetch(`${WS_SERVER_URL}/api/stats`);

    if (response.ok) {
      const stats = await response.json();
      return NextResponse.json(stats);
    } else {
      return NextResponse.json(
        { error: 'Failed to get stats' },
        { status: response.status }
      );
    }
  } catch (error) {
    console.error('Stats error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
