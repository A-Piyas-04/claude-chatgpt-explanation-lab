/**
 * Server-side API proxy.
 *
 * The browser never receives the researcher token or the API's address. The
 * token lives in the Next.js server process environment and is attached here,
 * which is what keeps §10's "never expose API keys in client-side bundles"
 * true of the web app as well as the API.
 *
 * Participant routes pass through the same proxy but carry no credential, so a
 * participant's browser cannot reach a researcher endpoint even if it guessed
 * the path: the API's own dependency injection rejects it.
 */

import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const RESEARCHER_API_TOKEN = process.env.RESEARCHER_API_TOKEN ?? "";

// Paths under /api/ that are participant-facing and must not be sent the
// researcher credential.
const PUBLIC_PREFIXES = ["p/"];

function isPublicPath(path: string): boolean {
  return PUBLIC_PREFIXES.some((prefix) => path.startsWith(prefix));
}

async function forward(request: NextRequest, path: string): Promise<NextResponse> {
  const search = request.nextUrl.search;
  const target = `${API_BASE_URL}/api/${path}${search}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (RESEARCHER_API_TOKEN && !isPublicPath(path)) {
    headers.set("authorization", `Bearer ${RESEARCHER_API_TOKEN}`);
  }

  let body: string | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.text();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
  } catch (error) {
    // A connection failure is the most common first-run problem, so say
    // precisely what to do about it rather than surfacing a bare stack.
    return NextResponse.json(
      {
        detail: {
          message:
            `Could not reach the ExplanationLab API at ${API_BASE_URL}. ` +
            `Start it with: cd apps/api && uvicorn explanationlab.main:app --reload`,
          error_type: "api_unreachable",
          cause: error instanceof Error ? error.message : String(error),
        },
      },
      { status: 503 },
    );
  }

  const responseBody = await upstream.text();
  const responseHeaders = new Headers();
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType) responseHeaders.set("content-type", upstreamType);
  const disposition = upstream.headers.get("content-disposition");
  if (disposition) responseHeaders.set("content-disposition", disposition);

  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type Params = { params: { path: string[] } };

export async function GET(request: NextRequest, { params }: Params) {
  return forward(request, params.path.join("/"));
}
export async function POST(request: NextRequest, { params }: Params) {
  return forward(request, params.path.join("/"));
}
export async function PATCH(request: NextRequest, { params }: Params) {
  return forward(request, params.path.join("/"));
}
export async function DELETE(request: NextRequest, { params }: Params) {
  return forward(request, params.path.join("/"));
}

export const dynamic = "force-dynamic";
