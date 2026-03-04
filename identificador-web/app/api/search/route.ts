export async function POST(req: Request) {
  const formData = await req.formData()
  const file = formData.get('file') as File

  const backendFormData = new FormData()
  backendFormData.append('file', file)

  const res = await fetch('http://localhost:8000/api/search', {
    method: 'POST',
    body: backendFormData
  })

  return Response.json(await res.json())
}