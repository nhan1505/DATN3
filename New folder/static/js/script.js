var gk_isXlsx = false;
var gk_xlsxFileLookup = {};
var gk_fileData = {};

function filledCell(cell) {
  return cell !== "" && cell != null;
}

function loadFileData(filename) {
  if (gk_isXlsx && gk_xlsxFileLookup[filename]) {
    try {
      var workbook = XLSX.read(gk_fileData[filename], { type: "base64" });
      var firstSheetName = workbook.SheetNames[0];
      var worksheet = workbook.Sheets[firstSheetName];
      var jsonData = XLSX.utils.sheet_to_json(worksheet, {
        header: 1,
        blankrows: false,
        defval: "",
      });
      var filteredData = jsonData.filter((row) => row.some(filledCell));
      var headerRowIndex = filteredData.findIndex(
        (row, index) =>
          row.filter(filledCell).length >=
          filteredData[index + 1]?.filter(filledCell).length
      );
      if (headerRowIndex === -1 || headerRowIndex > 25) {
        headerRowIndex = 0;
      }
      var csv = XLSX.utils.aoa_to_sheet(filteredData.slice(headerRowIndex));
      csv = XLSX.utils.sheet_to_csv(csv, { header: 1 });
      return csv;
    } catch (e) {
      console.error("Error parsing XLSX:", e);
      return "";
    }
  }
  return gk_fileData[filename] || "";
}

function calculateBMI() {
  const height = parseFloat(document.getElementById("height").value);
  const weight = parseFloat(document.getElementById("weight").value);
  if (isNaN(height) || isNaN(weight)) {
    document.getElementById("bmi-value").textContent = "N/A";
    document.getElementById("bmi").value = "";
    console.log("Invalid height or weight:", { height, weight });
    return null;
  }
  const bmi = weight / (height * height);
  document.getElementById("bmi-value").textContent = bmi.toFixed(2);
  document.getElementById("bmi").value = bmi.toFixed(2);
  document.getElementById("height-value").textContent = height.toFixed(2);
  document.getElementById("weight-value").textContent = weight.toFixed(0);
  console.log("Calculated BMI:", bmi);
  return bmi;
}

function showError(message) {
  const errorDiv = document.getElementById("error-message");
  if (errorDiv) {
    errorDiv.textContent = message;
    errorDiv.style.display = "block";
  }
  document.getElementById("loading").style.display = "none";
  console.error("Error displayed:", message);
}

function clearError() {
  const errorDiv = document.getElementById("error-message");
  if (errorDiv) errorDiv.style.display = "none";
}

function showLoading() {
  const loadingDiv = document.getElementById("loading");
  if (loadingDiv) loadingDiv.style.display = "block";
  const resultDiv = document.getElementById("prediction-result");
  if (resultDiv) resultDiv.style.display = "none";
  console.log("Showing loading spinner");
}

function hideLoading() {
  const loadingDiv = document.getElementById("loading");
  if (loadingDiv) loadingDiv.style.display = "none";
  console.log("Hiding loading spinner");
}

const predictionForm = document.getElementById("prediction-form");
if (predictionForm) {
  predictionForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearError();
    showLoading();
    console.log("Form submitted");

    const formData = new FormData(this);
    const bmi = calculateBMI();

    // Parse dữ liệu
    const data = {
      age: parseInt(formData.get("age")),
      sex: parseInt(formData.get("sex")),
      height: parseFloat(formData.get("height")),
      weight: parseFloat(formData.get("weight")),
      children: parseInt(formData.get("children")),
      smoker: parseInt(formData.get("smoker")),
      region: parseInt(formData.get("region")),
      model: formData.get("model"),
    };
    console.log("Form data:", data);

    // Validate dữ liệu
    if (isNaN(data.age) || data.age < 18 || data.age > 64) {
      showError("Tuổi phải từ 18 đến 64.");
      return;
    }
    if (isNaN(data.sex) || ![0, 1].includes(data.sex)) {
      showError("Giới tính không hợp lệ.");
      return;
    }
    if (isNaN(data.height) || data.height < 1.0 || data.height > 2.5) {
      showError("Chiều cao phải từ 1.0 đến 2.5 mét.");
      return;
    }
    if (isNaN(data.weight) || data.weight < 30 || data.weight > 150) {
      showError("Cân nặng phải từ 30 đến 150 kg.");
      return;
    }
    if (!bmi || bmi < 15 || bmi > 50) {
      showError("BMI phải từ 15 đến 50.");
      return;
    }
    if (isNaN(data.children) || data.children < 0 || data.children > 5) {
      showError("Số con cái phải từ 0 đến 5.");
      return;
    }
    if (isNaN(data.smoker) || ![0, 1].includes(data.smoker)) {
      showError("Tình trạng hút thuốc không hợp lệ.");
      return;
    }
    if (isNaN(data.region) || ![0, 1, 2, 3].includes(data.region)) {
      showError("Khu vực không hợp lệ.");
      return;
    }
    if (!["random_forest", "decision_tree"].includes(data.model)) {
      showError("Mô hình không hợp lệ.");
      return;
    }

    try {
      console.log("Sending POST to /predict:", JSON.stringify(data));
      const response = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      hideLoading();
      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorData = await response.json();
        let errorMsg;
        if (Array.isArray(errorData.detail)) {
          errorMsg = errorData.detail.map((e) => e.msg).join("; ");
        } else {
          errorMsg =
            errorData.detail || `HTTP error! status: ${response.status}`;
        }
        console.error("Server error:", errorData);
        throw new Error(errorMsg);
      }

      const result = await response.json();
      console.log("Prediction result:", result);

      const predictionText = document.getElementById("prediction-text");
      const predictionResult = document.getElementById("prediction-result");
      if (predictionText && predictionResult) {
        predictionText.textContent =
          result.prediction_text || "Không có kết quả";
        predictionResult.style.display = "block";
      } else {
        console.error("Prediction elements not found");
      }
    } catch (error) {
      console.error("Fetch error:", error);
      hideLoading();
      showError(`Lỗi: ${error.message}`);
      const predictionResult = document.getElementById("prediction-result");
      if (predictionResult) predictionResult.style.display = "none";
    }
  });
} else {
  console.error('Form with ID "prediction-form" not found');
  const errorDiv = document.getElementById("error-message");
  if (errorDiv) {
    errorDiv.textContent = "Lỗi: Không tìm thấy form dự đoán.";
    errorDiv.style.display = "block";
  }
}

// Initialize BMI calculation on page load
window.addEventListener("load", calculateBMI);
