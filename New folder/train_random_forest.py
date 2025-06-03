import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
import os
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Đọc dữ liệu
try:
    data = pd.read_csv('data/insurance.csv')
    logger.info("Đã đọc file 'insurance.csv' thành công.")
except FileNotFoundError:
    logger.error("Không tìm thấy file 'data/insurance.csv'.")
    exit(1)

# Kiểm tra cột
required_columns = ['age', 'sex', 'bmi', 'children', 'smoker', 'region', 'charges']
if not all(col in data.columns for col in required_columns):
    logger.error(f"Thiếu cột cần thiết. Các cột hiện có: {data.columns.tolist()}")
    exit(1)

# Chuyển đổi categorical variables
data['sex'] = data['sex'].map({'male': 0, 'female': 1})
data['smoker'] = data['smoker'].map({'no': 0, 'yes': 1})
data = pd.get_dummies(data, columns=['region'], prefix='region', drop_first=True)

# Xử lý giá trị thiếu
if data.isnull().any().any():
    logger.warning("Phát hiện giá trị thiếu, điền giá trị trung bình...")
    data = data.fillna(data.mean(numeric_only=True))

# Xử lý ngoại lệ
def remove_outliers(df, column, lower_quantile=0.01, upper_quantile=0.99):
    lower_bound = df[column].quantile(lower_quantile)
    upper_bound = df[column].quantile(upper_quantile)
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

data = remove_outliers(data, 'bmi')
data = remove_outliers(data, 'charges')
logger.info(f"Số mẫu sau khi loại bỏ ngoại lệ: {len(data)}")

# Chọn đặc trưng và nhãn
feature_columns = ['age', 'sex', 'bmi', 'children', 'smoker'] + [col for col in data.columns if col.startswith('region_')]
X = data[feature_columns]
y = data['charges']

# Chia dữ liệu
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
logger.info(f"Kích thước tập huấn luyện: {X_train.shape[0]} mẫu")
logger.info(f"Kích thước tập kiểm tra: {X_test.shape[0]} mẫu")

# Thiết lập hyperparameter
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [None, 10, 20],
    'min_samples_split': [2, 5],
    'min_samples_leaf': [1, 2],
    'max_features': ['sqrt', 'log2']
}

# Huấn luyện mô hình
rf = RandomForestRegressor(random_state=42)
logger.info("Bắt đầu tìm kiếm hyperparameter tối ưu...")
grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=5, scoring='r2', n_jobs=-1)
grid_search.fit(X_train, y_train)

# Lấy mô hình tốt nhất
best_model = grid_search.best_estimator_
logger.info(f"Hyperparameter tốt nhất: {grid_search.best_params_}")

# Đánh giá mô hình
def evaluate_model(model, X_train, X_test, y_train, y_test):
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    metrics = {
        'train_r2': r2_score(y_train, train_pred),
        'test_r2': r2_score(y_test, test_pred),
        'train_mae': mean_absolute_error(y_train, train_pred),
        'test_mae': mean_absolute_error(y_test, test_pred),
        'train_rmse': np.sqrt(mean_squared_error(y_train, train_pred)),
        'test_rmse': np.sqrt(mean_squared_error(y_test, test_pred))
    }
    logger.info(f"R² huấn luyện: {metrics['train_r2']:.4f}, R² kiểm tra: {metrics['test_r2']:.4f}")
    logger.info(f"MAE huấn luyện: {metrics['train_mae']:.2f}, MAE kiểm tra: {metrics['test_mae']:.2f}")
    logger.info(f"RMSE huấn luyện: {metrics['train_rmse']:.2f}, RMSE kiểm tra: {metrics['test_rmse']:.2f}")
    return metrics

metrics = evaluate_model(best_model, X_train, X_test, y_train, y_test)

# Lưu mô hình
try:
    os.makedirs('model', exist_ok=True)
    joblib.dump(best_model, 'model/random_forest_model.pkl')
    logger.info("Đã lưu mô hình Random Forest.")
except Exception as e:
    logger.error(f"Lỗi khi lưu mô hình: {e}")
    exit(1)