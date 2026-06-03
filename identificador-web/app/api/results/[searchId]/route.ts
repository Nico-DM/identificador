import { proxyToBackend } from "@/lib/backendFetch";

type RouteContext = {
  params: Promise<{
    searchId: string;
  }>;
};

export async function GET(req: Request, context: RouteContext) {
  const { searchId } = await context.params;
  return proxyToBackend(req, `/api/results/${searchId}`);
}
