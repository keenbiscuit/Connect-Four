

print("Connect Four project started.")

# import FastAPI from the fastapi package
from fastapi import FastAPI

# create FastAPI app instance
app = FastAPI()

# define health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}