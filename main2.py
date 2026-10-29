from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, Table, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from typing import Optional, List

# ==========================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS SQLITE
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# 2. TABLA INTERMEDIA (Muchos a Muchos: Usuarios <-> Materias)
# ==========================================
usuario_materia_association = Table(
    "usuario_materia",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), primary_key=True),
    Column("materia_id", Integer, ForeignKey("materias.id"), primary_key=True)
)


# ==========================================
# 3. MODELOS DE BASE DE DATOS (SQLAlchemy) con Relaciones
# ==========================================

class ParaleloModel(Base):
    """Tabla de Paralelos (Relación 1 a Muchos con Usuarios)"""
    __tablename__ = "paralelos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    aula = Column(String)
    capacidad = Column(Integer)
    
    usuarios = relationship("UsuarioModel", back_populates="paralelo")


class MateriaModel(Base):
    """Tabla de Materias (Relación Muchos a Muchos con Usuarios)"""
    __tablename__ = "materias"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    nombre = Column(String, index=True)
    creditos = Column(Integer)
    
    usuarios = relationship("UsuarioModel", secondary=usuario_materia_association, back_populates="materias")


class UsuarioModel(Base):
    """Tabla de Usuarios (Pertenece a 1 Paralelo y cursa muchas Materias)"""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    correo = Column(String, unique=True, index=True)
    rol = Column(String, default="Estudiante")
    
    paralelo_id = Column(Integer, ForeignKey("paralelos.id"), nullable=True)
    paralelo = relationship("ParaleloModel", back_populates="usuarios")
    
    materias = relationship("MateriaModel", secondary=usuario_materia_association, back_populates="usuarios")


# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)


# ==========================================
# 4. ESQUEMAS DE VALIDACIÓN (Pydantic)
# ==========================================

# --- ESQUEMAS PARA PARALELO ---
class ParaleloBase(BaseModel):
    nombre: str
    aula: str
    capacidad: int

class ParaleloCreate(ParaleloBase):
    pass

class ParaleloUpdate(BaseModel):
    nombre: Optional[str] = None
    aula: Optional[str] = None
    capacidad: Optional[int] = None

class ParaleloResponse(ParaleloBase):
    id: int
    model_config = {"from_attributes": True}


# --- ESQUEMAS PARA MATERIA ---
class MateriaBase(BaseModel):
    codigo: str
    nombre: str
    creditos: int

class MateriaCreate(MateriaBase):
    pass

class MateriaUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    creditos: Optional[int] = None

class MateriaResponse(MateriaBase):
    id: int
    model_config = {"from_attributes": True}


# --- ESQUEMAS PARA USUARIO ---
class UsuarioBase(BaseModel):
    nombre: str
    correo: str
    rol: Optional[str] = "Estudiante"
    paralelo_id: Optional[int] = None

class UsuarioCreate(UsuarioBase):
    pass

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[str] = None
    rol: Optional[str] = None
    paralelo_id: Optional[int] = None

class UsuarioResponse(UsuarioBase):
    id: int
    paralelo: Optional[ParaleloResponse] = None
    materias: List[MateriaResponse] = []
    model_config = {"from_attributes": True}


# ==========================================
# 5. INICIALIZACIÓN DE FASTAPI Y SEMBRADO DE >20 REGISTROS
# ==========================================

app = FastAPI(
    title="CRUD FastAPI & SQLite",
    description="API con las 3 tablas relacionales (Usuarios, Materias, Paralelos).",
    version="3.1"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def cargar_datos_iniciales():
    """Función para poblar automáticamente la base de datos con más de 20 registros iniciales y relaciones"""
    db = SessionLocal()
    
    if db.query(UsuarioModel).count() == 0:
        # 1. Crear Paralelos
        p1 = ParaleloModel(nombre="P1", aula="Aula 201", capacidad=35)
        p2 = ParaleloModel(nombre="P2", aula="Aula 202", capacidad=30)
        p3 = ParaleloModel(nombre="P3", aula="Laboratorio 1", capacidad=25)
        p4 = ParaleloModel(nombre="P4", aula="Laboratorio 2", capacidad=25)
        db.add_all([p1, p2, p3, p4])
        db.commit()

        # 2. Crear Materias
        m1 = MateriaModel(codigo="BD1", nombre="Base de Datos I", creditos=4)
        m2 = MateriaModel(codigo="PROG2", nombre="Programación Orientada a Objetos", creditos=5)
        m3 = MateriaModel(codigo="FIS1", nombre="Física General", creditos=3)
        m4 = MateriaModel(codigo="CALC1", nombre="Cálculo Diferencial", creditos=4)
        m5 = MateriaModel(codigo="ALGB", nombre="Álgebra Lineal", creditos=3)
        m6 = MateriaModel(codigo="EST1", nombre="Probabilidad y Estadística", creditos=4)
        db.add_all([m1, m2, m3, m4, m5, m6])
        db.commit()

        # 3. Crear Usuarios con sus relaciones
        u1 = UsuarioModel(nombre="Jeremy Maisincho", correo="jmaisinchoc@uce.edu.ec", rol="Estudiante", paralelo_id=p1.id, materias=[m1, m2])
        u2 = UsuarioModel(nombre="Cristian Perez", correo="cperez@uce.edu.ec", rol="Docente", paralelo_id=p1.id, materias=[m1])
        u3 = UsuarioModel(nombre="Ana Gomez", correo="agomez@uce.edu.ec", rol="Estudiante", paralelo_id=p2.id, materias=[m3, m4])
        u4 = UsuarioModel(nombre="Carlos Ruiz", correo="cruiz@uce.edu.ec", rol="Estudiante", paralelo_id=p2.id, materias=[m2, m5])
        u5 = UsuarioModel(nombre="Maria Lopez", correo="mlopez@uce.edu.ec", rol="Docente", paralelo_id=p3.id, materias=[m5, m6])
        u6 = UsuarioModel(nombre="Luis Fernandez", correo="lfernandez@uce.edu.ec", rol="Estudiante", paralelo_id=p3.id, materias=[m1, m6])
        u7 = UsuarioModel(nombre="Sofia Torres", correo="storres@uce.edu.ec", rol="Estudiante", paralelo_id=p4.id, materias=[m3, m4])
        u8 = UsuarioModel(nombre="David Morales", correo="dmorales@uce.edu.ec", rol="Administrador", paralelo_id=p4.id, materias=[m2])
        u9 = UsuarioModel(nombre="Valeria Castro", correo="vcastro@uce.edu.ec", rol="Estudiante", paralelo_id=p1.id, materias=[m4, m6])
        u10 = UsuarioModel(nombre="Mateo Silva", correo="msilva@uce.edu.ec", rol="Estudiante", paralelo_id=p2.id, materias=[m1, m3])
        u11 = UsuarioModel(nombre="Daniela Vera", correo="dvera@uce.edu.ec", rol="Estudiante", paralelo_id=p3.id, materias=[m2, m4])
        u12 = UsuarioModel(nombre="Esteban Quito", correo="equito@uce.edu.ec", rol="Estudiante", paralelo_id=p4.id, materias=[m5, m6])
        
        db.add_all([u1, u2, u3, u4, u5, u6, u7, u8, u9, u10, u11, u12])
        db.commit()
        print("¡Base de datos inicializada correctamente con registros y relaciones!")

    db.close()


# ==========================================
# 6. ENDPOINTS DEL CRUD - TABLA 1: USUARIOS
# ==========================================

@app.post("/usuarios/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(UsuarioModel).filter(UsuarioModel.correo == usuario.correo).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    nuevo = UsuarioModel(**usuario.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/usuarios/", response_model=List[UsuarioResponse], tags=["Usuarios"])
def obtener_usuarios(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(UsuarioModel).offset(skip).limit(limit).all()

@app.get("/usuarios/{usuario_id}", response_model=UsuarioResponse, tags=["Usuarios"])
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return usuario

@app.put("/usuarios/{usuario_id}", response_model=UsuarioResponse, tags=["Usuarios"])
def reemplazar_usuario(usuario_id: int, usuario_datos: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    usuario.nombre = usuario_datos.nombre
    usuario.correo = usuario_datos.correo
    usuario.rol = usuario_datos.rol
    usuario.paralelo_id = usuario_datos.paralelo_id
    db.commit()
    db.refresh(usuario)
    return usuario

@app.patch("/usuarios/{usuario_id}", response_model=UsuarioResponse, tags=["Usuarios"])
def actualizar_usuario_parcial(usuario_id: int, usuario_datos: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    datos_dict = usuario_datos.model_dump(exclude_unset=True)
    for clave, valor in datos_dict.items():
        setattr(usuario, clave, valor)
        
    db.commit()
    db.refresh(usuario)
    return usuario

@app.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Usuarios"])
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    db.delete(usuario)
    db.commit()
    return None


# ==========================================
# 7. ENDPOINTS DEL CRUD - TABLA 2: MATERIAS
# ==========================================

@app.post("/materias/", response_model=MateriaResponse, status_code=status.HTTP_201_CREATED, tags=["Materias"])
def crear_materia(materia: MateriaCreate, db: Session = Depends(get_db)):
    if db.query(MateriaModel).filter(MateriaModel.codigo == materia.codigo).first():
        raise HTTPException(status_code=400, detail="El código de la materia ya existe.")
    nuevo = MateriaModel(**materia.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/materias/", response_model=List[MateriaResponse], tags=["Materias"])
def obtener_materias(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(MateriaModel).offset(skip).limit(limit).all()

@app.get("/materias/{materia_id}", response_model=MateriaResponse, tags=["Materias"])
def obtener_materia(materia_id: int, db: Session = Depends(get_db)):
    materia = db.query(MateriaModel).filter(MateriaModel.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    return materia

@app.put("/materias/{materia_id}", response_model=MateriaResponse, tags=["Materias"])
def reemplazar_materia(materia_id: int, materia_datos: MateriaCreate, db: Session = Depends(get_db)):
    materia = db.query(MateriaModel).filter(MateriaModel.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    
    materia.codigo = materia_datos.codigo
    materia.nombre = materia_datos.nombre
    materia.creditos = materia_datos.creditos
    db.commit()
    db.refresh(materia)
    return materia

@app.patch("/materias/{materia_id}", response_model=MateriaResponse, tags=["Materias"])
def actualizar_materia_parcial(materia_id: int, materia_datos: MateriaUpdate, db: Session = Depends(get_db)):
    materia = db.query(MateriaModel).filter(MateriaModel.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    
    datos_dict = materia_datos.model_dump(exclude_unset=True)
    for clave, valor in datos_dict.items():
        setattr(materia, clave, valor)
        
    db.commit()
    db.refresh(materia)
    return materia

@app.delete("/materias/{materia_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Materias"])
def eliminar_materia(materia_id: int, db: Session = Depends(get_db)):
    materia = db.query(MateriaModel).filter(MateriaModel.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    db.delete(materia)
    db.commit()
    return None


# ==========================================
# 8. ENDPOINTS DEL CRUD - TABLA 3: PARALELOS
# ==========================================

@app.post("/paralelos/", response_model=ParaleloResponse, status_code=status.HTTP_201_CREATED, tags=["Paralelos"])
def crear_paralelo(paralelo: ParaleloCreate, db: Session = Depends(get_db)):
    nuevo = ParaleloModel(**paralelo.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/paralelos/", response_model=List[ParaleloResponse], tags=["Paralelos"])
def obtener_paralelos(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(ParaleloModel).offset(skip).limit(limit).all()

@app.get("/paralelos/{paralelo_id}", response_model=ParaleloResponse, tags=["Paralelos"])
def obtener_paralelo(paralelo_id: int, db: Session = Depends(get_db)):
    paralelo = db.query(ParaleloModel).filter(ParaleloModel.id == paralelo_id).first()
    if not paralelo:
        raise HTTPException(status_code=404, detail="Paralelo no encontrado.")
    return paralelo

@app.put("/paralelos/{paralelo_id}", response_model=ParaleloResponse, tags=["Paralelos"])
def reemplazar_paralelo(paralelo_id: int, paralelo_datos: ParaleloCreate, db: Session = Depends(get_db)):
    paralelo = db.query(ParaleloModel).filter(ParaleloModel.id == paralelo_id).first()
    if not paralelo:
        raise HTTPException(status_code=404, detail="Paralelo no encontrado.")
    
    paralelo.nombre = paralelo_datos.nombre
    paralelo.aula = paralelo_datos.aula
    paralelo.capacidad = paralelo_datos.capacidad
    db.commit()
    db.refresh(paralelo)
    return paralelo

@app.patch("/paralelos/{paralelo_id}", response_model=ParaleloResponse, tags=["Paralelos"])
def actualizar_paralelo_parcial(paralelo_id: int, paralelo_datos: ParaleloUpdate, db: Session = Depends(get_db)):
    paralelo = db.query(ParaleloModel).filter(ParaleloModel.id == paralelo_id).first()
    if not paralelo:
        raise HTTPException(status_code=404, detail="Paralelo no encontrado.")
    
    datos_dict = paralelo_datos.model_dump(exclude_unset=True)
    for clave, valor in datos_dict.items():
        setattr(paralelo, clave, valor)
        
    db.commit()
    db.refresh(paralelo)
    return paralelo

@app.delete("/paralelos/{paralelo_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Paralelos"])
def eliminar_paralelo(paralelo_id: int, db: Session = Depends(get_db)):
    paralelo = db.query(ParaleloModel).filter(ParaleloModel.id == paralelo_id).first()
    if not paralelo:
        raise HTTPException(status_code=404, detail="Paralelo no encontrado.")
    db.delete(paralelo)
    db.commit()
    return None