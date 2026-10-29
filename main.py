from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. Configuración de la Base de Datos SQLite (se guardará localmente como 'database.db')
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Definición del Modelo de la Base de Datos (SQLAlchemy)
class UsuarioModel(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    correo = Column(String, unique=True, index=True)

# Crear las tablas en la base de datos automáticamente
Base.metadata.create_all(bind=engine)

# 3. Esquemas de Pydantic (Validación de datos de entrada y salida)
class UsuarioBase(BaseModel):
    nombre: str
    correo: str

class UsuarioCreate(UsuarioBase):
    pass

class UsuarioResponse(UsuarioBase):
    id: int

    model_config = {"from_attributes": True} # Compatible con Pydantic V2

# 4. Inicialización de la aplicación FastAPI
app = FastAPI(
    title="CRUD con FastAPI y SQLite",
    description="Proyecto base para el desarrollo de software",
    version="1.0"
)

# Dependencia para obtener la sesión de la base de datos por cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 5. ENDPOINTS DEL CRUD ---

# CREATE (Crear usuario)
@app.post("/usuarios/", response_model=UsuarioResponse, status_code=201)
def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si el correo ya existe
    db_usuario = db.query(UsuarioModel).filter(UsuarioModel.correo == usuario.correo).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")
    
    nuevo_usuario = UsuarioModel(nombre=usuario.nombre, correo=usuario.correo)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

# READ ALL (Obtener todos los usuarios con paginación básica)
@app.get("/usuarios/", response_model=list[UsuarioResponse])
def obtener_usuarios(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    usuarios = db.query(UsuarioModel).offset(skip).limit(limit).all()
    return usuarios

# READ ONE (Obtener un usuario por su ID)
@app.get("/usuarios/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return usuario

# UPDATE (Actualizar un usuario)
@app.put("/usuarios/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(usuario_id: int, usuario_actualizado: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    usuario.nombre = usuario_actualizado.nombre
    usuario.correo = usuario_actualizado.correo
    db.commit()
    db.refresh(usuario)
    return usuario

# DELETE (Eliminar un usuario)
@app.delete("/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    db.delete(usuario)
    db.commit()
    return None