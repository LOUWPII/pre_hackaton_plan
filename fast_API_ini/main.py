import uvicorn

#0.0.0.0 run it on any availabe domain, it will run in localhost.
#port 8000
if __name__ == "__main__":
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000, reload=True)