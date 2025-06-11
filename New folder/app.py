from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, EmailStr
import joblib
import numpy as np
import pandas as pd
import sqlite3
import logging
from typing import Literal, Optional
from starlette.responses import FileResponse, JSONResponse
import os
import time
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import json
import traceback

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Custom 500 handler
@app.exception_handler(Exception)
async def custom_500_handler(request: Request, exc: Exception):
    error_msg = f"Internal Server Error: {str(exc)}"
    stack_trace = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"{error_msg}\n{stack_trace}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Lỗi server, vui lòng thử lại sau."}
    )

# Cấu hình thư mục
required_dirs = ['static/css', 'static/js', 'templates', 'model', 'data']
for dir_path in required_dirs:
    if not os.path.exists(dir_path):
        logger.error(f"Thư mục '{dir_path}' không tồn tại.")
        raise FileNotFoundError(f"Thư mục '{dir_path}' không tồn tại.")

# Tùy chỉnh StaticFiles
class CustomStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        full_path = os.path.join(self.directory, path)
        logger.debug(f"Yêu cầu tệp tĩnh: {path}, đường dẫn thực: {full_path}")
        if not os.path.exists(full_path):
            logger.warning(f"Tệp tĩnh không tồn tại: {full_path}")
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

# Mount static files
app.mount("/static", CustomStaticFiles(directory="static"), name="static")
logger.info("Mounted static files at /static")

# Thiết lập templates
templates = Jinja2Templates(directory="templates")

# Cấu hình JWT
SECRET_KEY = "your-secret-key-please-change-this-in-production"  # Thay đổi trong production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Cấu hình mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Khởi tạo CSDL
def init_db():
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY,
                    age INTEGER,
                    sex INTEGER,
                    height REAL,
                    weight REAL,
                    children INTEGER,
                    smoker INTEGER,
                    region INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    input_data JSON,
                    prediction REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
        logger.info("Khởi tạo cơ sở dữ liệu thành công")
    except sqlite3.Error as e:
        logger.error(f"Lỗi khởi tạo cơ sở dữ liệu: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khởi tạo cơ sở dữ liệu")

init_db()

# Tải mô hình
models = {}
try:
    if os.path.exists('model/random_forest_model.pkl'):
        models['random_forest'] = joblib.load('model/random_forest_model.pkl')
        logger.info("Đã tải mô hình Random Forest.")
    else:
        logger.error("Tệp random_forest_model.pkl không tồn tại.")
        raise FileNotFoundError("Tệp random_forest_model.pkl không tồn tại.")
    if os.path.exists('model/decision_tree_model.pkl'):
        models['decision_tree_model'] = joblib.load('model/decision_tree_model.pkl')
        logger.info("Đã tải mô hình Decision Tree.")
    else:
        logger.error("Tệp decision_tree_model.pkl không tồn tại.")
        raise FileNotFoundError("Tệp decision_tree_model.pkl không tồn tại.")
except Exception as e:
    logger.error(f"Lỗi khi tải mô hình: {e}")
    raise HTTPException(status_code=500, detail=f"Không thể tải mô hình: {str(e)}")

# Tỷ giá USD sang VND
USD_TO_VND = 25000

# Mô hình dữ liệu
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class ProfileInput(BaseModel):
    age: int = Field(..., ge=18, le=64)
    sex: int = Field(..., ge=0, le=1)
    height: float = Field(..., ge=1.0, le=2.5)
    weight: float = Field(..., ge=30, le=150)
    children: int = Field(..., ge=0, le=5)
    smoker: int = Field(..., ge=0, le=1)
    region: int = Field(..., ge=0, le=3)

class UserOut(BaseModel):
    id: int
    email: str

class PredictionInput(BaseModel):
    age: int = Field(..., ge=18, le=64)
    sex: int = Field(..., ge=0, le=1)
    height: float = Field(..., ge=1.0, le=2.5)
    weight: float = Field(..., ge=30, le=150)
    children: int = Field(..., ge=0, le=5)
    smoker: int = Field(..., ge=0, le=1)
    region: int = Field(..., ge=0, le=3)
    model: Literal['random_forest', 'decision_tree_model']

# Hàm xác thực
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        logger.debug("No token provided")
        return None
    credentials_exception = HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.error("Token missing user_id")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        raise credentials_exception
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email FROM users WHERE id = ?", (int(user_id),))
            user = cursor.fetchone()
            if user is None:
                logger.error(f"User not found for id: {user_id}")
                raise credentials_exception
        return {"id": user[0], "email": user[1]}
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi truy vấn cơ sở dữ liệu")

# Kiểm tra trạng thái đăng nhập
@app.get("/me", response_model=UserOut)
async def get_me(current_user: Optional[dict] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    logger.info(f"User authenticated: {current_user['email']}")
    return current_user

# Custom 404 handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    path = request.url.path
    if 'com.chrome.devtools.json' in path:
        logger.debug(f"Ignored 404 for Chrome DevTools request: {path}")
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    logger.warning(f"404 Not Found: {path}")
    return JSONResponse(status_code=404, content={"detail": f"Resource not found: {path}"})

# Trang chủ
@app.get("/")
async def home(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    try:
        query_params = dict(request.query_params)
        if any(key in query_params for key in ['age', 'sex', 'height', 'weight', 'children', 'smoker', 'region', 'model']):
            logger.warning(f"Nhận GET request với query params dự đoán: {query_params}")
        logger.info(f"Truy cập trang chủ, user: {current_user['email'] if current_user else 'None'}")
        return templates.TemplateResponse("index.html", {"request": request, "timestamp": int(time.time()), "user": current_user})
    except Exception as e:
        logger.error(f"Lỗi khi truy cập trang chủ: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi tải trang chủ")

# Đăng ký
@app.post("/register")
async def register(input_data: RegisterInput):
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (input_data.email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email đã được sử dụng")
            hashed_password = get_password_hash(input_data.password)
            cursor.execute(
                "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
                (input_data.email, hashed_password)
            )
            conn.commit()
        logger.info(f"Đăng ký thành công cho email: {input_data.email}")
        return {"message": "Đăng ký thành công"}
    except sqlite3.Error as e:
        logger.error(f"Lỗi cơ sở dữ liệu khi đăng ký: {e}")
        raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi đăng ký")
    except Exception as e:
        logger.error(f"Lỗi khi đăng ký: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi server")

# Đăng nhập
@app.post("/login")
async def login(input_data: LoginInput):
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, hashed_password FROM users WHERE email = ?", (input_data.email,))
            user = cursor.fetchone()
            if not user or not verify_password(input_data.password, user[1]):
                raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(data={"sub": str(user[0])}, expires_delta=access_token_expires)
        logger.info(f"Đăng nhập thành công cho email: {input_data.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except sqlite3.Error as e:
        logger.error(f"Lỗi cơ sở dữ liệu khi đăng nhập: {e}")
        raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi đăng nhập")
    except Exception as e:
        logger.error(f"Lỗi khi đăng nhập: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi server")

# Cập nhật hồ sơ
@app.put("/profile")
async def update_profile(input_data: ProfileInput, current_user: Optional[dict] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO profiles (user_id, age, sex, height, weight, children, smoker, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user["id"],
                    input_data.age,
                    input_data.sex,
                    input_data.height,
                    input_data.weight,
                    input_data.children,
                    input_data.smoker,
                    input_data.region
                )
            )
            conn.commit()
        logger.info(f"Cập nhật hồ sơ thành công cho user_id: {current_user['id']}")
        return {"message": "Cập nhật hồ sơ thành công"}
    except sqlite3.Error as e:
        logger.error(f"Lỗi cơ sở dữ liệu khi cập nhật hồ sơ: {e}")
        raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi cập nhật hồ sơ")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật hồ sơ: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi server")

# Dự đoán
@app.post("/predict")
async def predict(input_data: PredictionInput, current_user: Optional[dict] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        logger.info(f"Nhận dữ liệu dự đoán: {input_data.dict()}")
        
        # Tính BMI
        bmi = input_data.weight / (input_data.height ** 2)
        logger.debug(f"Tính BMI: {bmi:.2f}")
        if not (15 <= bmi <= 50):
            logger.warning(f"BMI ngoài khoảng hợp lệ: {bmi:.2f}")
            raise HTTPException(status_code=400, detail="BMI phải nằm trong khoảng 15-50.")

        # Chuẩn bị dữ liệu đầu vào
        feature_columns = ['age', 'sex', 'bmi', 'children', 'smoker', 'region']
        input_df = pd.DataFrame({
            'age': [input_data.age],
            'sex': [input_data.sex],
            'bmi': [bmi],
            'children': [input_data.children],
            'smoker': [input_data.smoker],
            'region': [input_data.region]
        }, columns=feature_columns)
        logger.debug(f"Dữ liệu đầu vào mô hình: {input_df.to_dict()}")

        # Dự đoán
        model = models.get(input_data.model)
        if model is None:
            logger.error(f"Mô hình không hợp lệ: {input_data.model}")
            raise HTTPException(status_code=400, detail="Mô hình không hợp lệ.")
        
        prediction_usd = model.predict(input_df)[0]
        logger.debug(f"Dự đoán USD: {prediction_usd}")
        if prediction_usd < 0:
            logger.warning(f"Dự đoán âm: {prediction_usd}")
            prediction_usd = 0
        prediction_vnd = prediction_usd * USD_TO_VND
        prediction_vnd_formatted = "{:,.0f}".format(prediction_vnd)

        model_name = "Random Forest" if input_data.model == "random_forest" else "Decision Tree"
        response = {
            "prediction": prediction_vnd,
            "prediction_text": f"Số tiền bảo hiểm dự đoán (mô hình {model_name}): {prediction_vnd_formatted} VND"
        }

        # Lưu vào lịch sử
        try:
            with sqlite3.connect("database.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO predictions (user_id, input_data, prediction)
                    VALUES (?, ?, ?)
                    """,
                    (current_user["id"], json.dumps(input_data.dict()), prediction_vnd)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Lỗi cơ sở dữ liệu khi lưu dự đoán: {e}")
            raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi lưu dự đoán")

        logger.info(f"Dự đoán thành công: {response['prediction_text']}")
        return response
    except Exception as e:
        logger.error(f"Lỗi khi dự đoán: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý dữ liệu đầu vào: {str(e)}")

# Xem lịch sử dự đoán
@app.get("/history")
async def get_history(current_user: Optional[dict] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, input_data, prediction, timestamp FROM predictions WHERE user_id = ? ORDER BY timestamp DESC",
                (current_user["id"],)
            )
            history = [
                {
                    "id": row[0],
                    "input_data": json.loads(row[1]),
                    "prediction": row[2],
                    "timestamp": row[3]
                }
                for row in cursor.fetchall()
            ]
        logger.info(f"Lấy lịch sử dự đoán cho user_id: {current_user['id']}")
        return history
    except sqlite3.Error as e:
        logger.error(f"Lỗi cơ sở dữ liệu khi lấy lịch sử: {e}")
        raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi lấy lịch sử")
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi server")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")