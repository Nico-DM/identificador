from fastapi import FastAPI, UploadFile, File
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

@app.post("/api/search")
async def search(file: UploadFile = File(...)):
    # TODO: Implementar búsqueda
    return {"search_id": "123", "status": "processing"}

@app.get("/api/results/{search_id}")
async def get_results(search_id: str):
    # TODO: Implementar obtención de resultados
    return {"status": "done", "results": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)