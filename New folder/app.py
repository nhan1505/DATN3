from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import joblib
import numpy as np
import pandas as pd
import logging
from typing import Literal
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
import os
import time

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Kiểm tra thư mục
required_dirs = ['static/css', 'static/js', 'templates', 'model']
for dir_path in required_dirs:
    if not os.path.exists(dir_path):
        logger.error(f"Thư mục '{dir_path}' không tồn tại.")
        raise FileNotFoundError(f"Thư mục '{dir_path}' không tồn tại.")

# Tùy chỉnh StaticFiles để kiểm soát cache và log
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

# Tải mô hình
try:
    models = {
        'random_forest': joblib.load('model/random_forest_model.pkl'),
        'decision_tree': joblib.load('model/decision_tree_model.pkl')
    }
    logger.info("Đã tải mô hình Decision Tree và Random Forest.")
except FileNotFoundError as e:
    logger.error(f"Lỗi khi tải mô hình: {e}")
    raise HTTPException(status_code=500, detail="Không thể tải mô hình.")

# Tỷ giá USD sang VND
USD_TO_VND = 25000

# Định nghĩa mô hình dữ liệu đầu vào
class PredictionInput(BaseModel):
    age: int = Field(..., ge=18, le=64, description="Tuổi từ 18 đến 64")
    sex: int = Field(..., ge=0, le=1, description="Giới tính: 0 (Nam) hoặc 1 (Nữ)")
    height: float = Field(..., ge=1.0, le=2.5, description="Chiều cao từ 1.0 đến 2.5 mét")
    weight: float = Field(..., ge=30, le=150, description="Cân nặng từ 30 đến 150 kg")
    children: int = Field(..., ge=0, le=5, description="Số con cái từ 0 đến 5")
    smoker: int = Field(..., ge=0, le=1, description="Hút thuốc: 0 (Không) hoặc 1 (Có)")
    region: int = Field(..., ge=0, le=3, description="Khu vực: 0 (southwest), 1 (southeast), 2 (northwest), 3 (northeast)")
    model: Literal['random_forest', 'decision_tree'] = Field(..., description="Mô hình: random_forest hoặc decision_tree")

# Custom 404 handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    path = request.url.path
    if 'com.chrome.devtools.json' in path:
        logger.debug(f"Ignored 404 for Chrome DevTools request: {path}")
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    logger.warning(f"404 Not Found: {path}")
    return JSONResponse(status_code=404, content={"detail": f"Resource not found: {path}"})

# Route cho trang chủ
@app.get("/")
async def home(request: Request):
    query_params = dict(request.query_params)
    if any(key in query_params for key in ['age', 'sex', 'height', 'weight', 'children', 'smoker', 'region', 'model']):
        logger.warning(f"Nhận GET request với query params dự đoán: {query_params}")
    logger.info("Truy cập trang chủ")
    return templates.TemplateResponse("index.html", {"request": request, "timestamp": int(time.time())})

# Route cho dự đoán
@app.post("/predict")
async def predict(input_data: PredictionInput):
    try:
        logger.info(f"Nhận dữ liệu dự đoán: {input_data.dict()}")
        
        # Tính BMI
        bmi = input_data.weight / (input_data.height ** 2)
        logger.debug(f"Tính BMI: {bmi:.2f}")
        if not (15 <= bmi <= 50):
            logger.warning(f"BMI ngoài khoảng hợp lệ: {bmi:.2f}")
            raise HTTPException(status_code=400, detail="BMI phải nằm trong khoảng 15-50.")

        # Chuẩn bị dữ liệu đầu vào
        region_map = {0: 'southwest', 1: 'southeast', 2: 'northwest', 3: 'northeast'}
        region_str = region_map.get(input_data.region, None)
        if region_str is None:
            logger.error(f"Khu vực không hợp lệ: {input_data.region}")
            raise HTTPException(status_code=400, detail="Khu vực không hợp lệ.")

        feature_columns = ['age', 'sex', 'bmi', 'children', 'smoker', 'region_northwest', 'region_southeast', 'region_southwest']
        input_df = pd.DataFrame({
            'age': [input_data.age],
            'sex': [input_data.sex],
            'bmi': [bmi],
            'children': [input_data.children],
            'smoker': [input_data.smoker],
            'region_northwest': [1 if region_str == 'northwest' else 0],
            'region_southeast': [1 if region_str == 'southeast' else 0],
            'region_southwest': [1 if region_str == 'southwest' else 0]
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
        logger.info(f"Dự đoán thành công: {response['prediction_text']}")
        return response
    except Exception as e:
        logger.error(f"Lỗi khi dự đoán: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Lỗi xử lý dữ liệu đầu vào: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")