from fastapi import FastAPI, File, HTTPException, UploadFile, Form, Depends 
from app.schema import PostCreate, PostResponse
from app.db import Post, create_db_and_tables, get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid
import tempfile
from app.users import auth_backend, fastapi_users, current_active_user
from app.schema import UserRead, UserCreate, UserUpdate






@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: create database and tables
    await create_db_and_tables()
    yield
    # Shutdown code (if any) can go here


app = FastAPI(lifespan=lifespan)

#include all the endpoints related to user authentication provided by FastAPI Users
#JWT auth endpoints will be available under /auth/jwt
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


#Dependency Injection example for file upload
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    #Protect the route to authenticated users only
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    #Save the uploaded file to a temporary location
    temp_file_path = None
    #Use a temp file to store the uploaded file
    try:
        #Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            #Get the temp file path
            temp_file_path = temp_file.name
            #Copy the uploaded file content to the temp file
            shutil.copyfileobj(file.file, temp_file)
        #Upload the file to ImageKit
        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        if upload_result.response_metadata.http_status_code == 200:
            post = Post(
                user_id=user.id,
                caption=caption,
                url=upload_result.url,
                file_type="video" if file.content_type.startswith("video/") else "image",
                file_name=upload_result.name
            )
            #Add to database session - staged
            session.add(post)
            #Commit to database
            await session.commit()
            #Refresh to get the new data from DB including the ID and date
            await session.refresh(post)
            #Return the post data
            return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        #Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()    


@app.get("/feed")
async def get_feed(session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):
    #Query all posts ordered by created_at descending
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    #row[0] to get the first and only Post object from the row tuple
    #the loop takes each row and gets the Post object
    posts = [row[0] for row in result.fetchall()]

    result = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}
    posts_data = []
    #Build list of posts data retrieved in dictionary format from posts objects
    for post in posts:
        posts_data.append({
            "id": post.id,
            "user_id": str(post.user_id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(),
            "is_owner": post.user_id == user.id,
            "email": user_dict.get(post.user_id, "Unknown")
        })
    return {"posts": posts_data}


@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):
    try:
        post_uuid = uuid.UUID(post_id)
        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        await session.delete(post)

        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        await session.commit()

        return {"success": True, "message": "Post deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




"""
========================= Basic FastAPI Application =========================
This application demonstrates basic CRUD operations using FastAPI.
==============================================================================


text_post = {
    1: {
        "title": "Inicio del Proyecto",
        "content": "Configuración inicial del entorno virtual y FastAPI."
    },
    2: {
        "title": "Rutas y Endpoints",
        "content": "Definiendo los primeros endpoints GET y POST en el archivo principal."
    },
    3: {
        "title": "Modelos Pydantic",
        "content": "Creación de los esquemas de datos para asegurar la entrada y salida de la API."
    },
    4: {
        "title": "Despliegue y Pruebas",
        "content": "Documentación y preparación para el despliegue en un servicio de hosting."
    }
}

#lets use query parameters
#We always use python type hint
@app.get("/posts")
async def get_all_posts(limit: int = None):
    if limit:
        return list(text_post.values())[:limit]
    return text_post

@app.get("/posts/{id}")
#mapping id parameter from the path
async def get_post(id: int) -> PostResponse:
    if id not in text_post:
        raise HTTPException(status_code=404, detail="Post not found")
    return text_post.get(id)

#Lets use request body with an schema
@app.post("/posts")
def create_post(post: PostCreate) -> PostResponse:
    new_post = {"title": post.title, "content": post.content}
    text_post[max(text_post.keys())+1] = new_post
    return new_post

"""