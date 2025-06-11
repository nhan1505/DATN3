import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import pickle
import os

# Define paths
DATA_PATH = 'data/insurance.csv'
MODEL_PATH = 'model/decision_tree_model.pkl'

# Ensure model directory exists
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

# Load dataset
try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    print(f"Error: {DATA_PATH} not found.")
    exit(1)

# Preprocess data
# Map categorical variables
df['sex'] = df['sex'].map({'male': 0, 'female': 1})
df['smoker'] = df['smoker'].map({'no': 0, 'yes': 1})
df['region'] = df['region'].map({'southwest': 0, 'southeast': 1, 'northwest': 2, 'northeast': 3})

# Calculate BMI if not present
if 'bmi' not in df.columns and 'height' in df.columns and 'weight' in df.columns:
    df['bmi'] = df['weight'] / (df['height'] ** 2)

# Select features and target
features = ['age', 'sex', 'bmi', 'children', 'smoker', 'region']
X = df[features]
y = df['charges']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize and train model
model = DecisionTreeRegressor(random_state=42)
model.fit(X_train, y_train)

# Make predictions
train_pred = model.predict(X_train)
test_pred = model.predict(X_test)

# Calculate metrics
metrics = {
    'train_r2': r2_score(y_train, train_pred),
    'test_r2': r2_score(y_test, test_pred),
    'train_mae': mean_absolute_error(y_train, train_pred),
    'test_mae': mean_absolute_error(y_test, test_pred),
    'train_rmse': np.sqrt(mean_squared_error(y_train, train_pred)),
    'test_rmse': np.sqrt(mean_squared_error(y_test, test_pred))
}

# Print metrics
print("Decision Tree Model Metrics:")
for key, value in metrics.items():
    print(f"{key}: {value:.4f}")

# Save model
try:
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to {MODEL_PATH}")
except Exception as e:
    print(f"Error saving model: {e}")