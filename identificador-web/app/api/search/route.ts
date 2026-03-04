export async function POST(req: Request) {
  // Mock: devolver resultados hardcodeados
  return Response.json({
    status: 'done',
    results: [
      { date: '2023-01-15', platform: 'instagram', url: 'https://...', score: 0.95 }
    ]
  })
}