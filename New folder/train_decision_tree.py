import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Đọc dữ liệu
try:
    df = pd.read_csv('data/insurance.csv')
    logger.info("Đã đọc dữ liệu từ insurance.csv")
except FileNotFoundError:
    logger.error("Tệp insurance.csv không tồn tại")
    raise

# Kiểm tra cột
expected_columns = ['age', 'sex', 'bmi', 'children', 'smoker', 'region', 'charges']
if not all(col in df.columns for col in expected_columns):
    logger.error(f"Dữ liệu thiếu cột: {set(expected_columns) - set(df.columns)}")
    raise ValueError("Dữ liệu thiếu cột cần thiết")

# Mã hóa biến phân loại
le_sex = LabelEncoder()
le_smoker = LabelEncoder()
df['sex'] = le_sex.fit_transform(df['sex'])
df['smoker'] = le_smoker.fit_transform(df['smoker'])

# Mã hóa one-hot cho region
df = pd.get_dummies(df, columns=['region'], prefix='region')
logger.info(f"Cột sau khi mã hóa: {df.columns.tolist()}")

# Đặc trưng và nhãn
feature_columns = ['age', 'sex', 'bmi', 'children', 'smoker'] + [col for col in df.columns if col.startswith('region_')]
if 'region_southwest' not in df.columns:
    logger.warning("Không tìm thấy region_southwest, thêm cột giả")
    df['region_southwest'] = 0
feature_columns = [col for col in feature_columns if col != 'region_northeast']  # Loại bỏ region_northeast nếu là tham chiếu
X = df[feature_columns]
y = df['charges']
logger.info(f"Đặc trưng sử dụng: {feature_columns}")

# Chia dữ liệu
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Huấn luyện mô hình
model = DecisionTreeRegressor(random_state=42)
model.fit(X_train, y_train)
logger.info("Đã huấn luyện mô hình Decision Tree")

# Lưu mô hình và LabelEncoder
joblib.dump(model, 'model/decision_tree.pkl')
joblib.dump(le_sex, 'model/le_sex.pkl')
joblib.dump(le_smoker, 'model/le_smoker.pkl')
logger.info("Đã lưu mô hình và LabelEncoder")

# Đánh giá
y_pred = model.predict(X_test)
mse = np.mean((y_pred - y_test) ** 2)
logger.info(f"Mean Squared Error trên tập kiểm tra: {mse:.2f}")