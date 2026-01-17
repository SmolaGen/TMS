from fastapi import FastAPI

app = FastAPI(title="Order Management API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Order Management API"}
