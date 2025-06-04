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

function calculateProfileBMI() {
  const height = parseFloat(document.getElementById("profile-height").value);
  const weight = parseFloat(document.getElementById("profile-weight").value);
  if (isNaN(height) || isNaN(weight)) {
    document.getElementById("profile-bmi-value").textContent = "N/A";
    document.getElementById("profile-bmi").value = "";
    return null;
  }
  const bmi = weight / (height * height);
  document.getElementById("profile-bmi-value").textContent = bmi.toFixed(2);
  document.getElementById("profile-bmi").value = bmi.toFixed(2);
  document.getElementById("profile-height-value").textContent =
    height.toFixed(2);
  document.getElementById("profile-weight-value").textContent =
    weight.toFixed(0);
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

function showSuccess(message) {
  const successDiv = document.getElementById("success-message");
  if (successDiv) {
    successDiv.textContent = message;
    successDiv.style.display = "block";
  }
  document.getElementById("loading").style.display = "none";
}

function clearMessages() {
  const errorDiv = document.getElementById("error-message");
  const successDiv = document.getElementById("success-message");
  if (errorDiv) errorDiv.style.display = "none";
  if (successDiv) successDiv.style.display = "none";
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

function showSection(sectionId) {
  const sections = [
    "register-form",
    "login-form",
    "profile-form",
    "predict-form",
    "history-form",
  ];
  sections.forEach((id) => {
    const section = document.getElementById(id);
    if (section) section.style.display = id === sectionId ? "block" : "none";
  });
  clearMessages();
}

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function removeToken() {
  localStorage.removeItem("access_token");
}

function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

function validatePassword(password) {
  const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/;
  return re.test(password);
}

async function checkAuthStatus() {
  const token = getToken();
  if (!token) {
    showSection("login-form");
    return { authenticated: false, user: null };
  }
  try {
    const response = await fetch("/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      console.warn(`GET /me failed with status: ${response.status}`);
      removeToken();
      showSection("login-form");
      return { authenticated: false, user: null };
    }
    const user = await response.json();
    showSection("predict-form");
    return { authenticated: true, user };
  } catch (error) {
    console.error("Error checking auth status:", error);
    removeToken();
    showSection("login-form");
    return { authenticated: false, user: null };
  }
}

async function updateNavbar() {
  const { authenticated, user } = await checkAuthStatus();
  const navList = document.querySelector("nav ul");
  if (!navList) {
    console.error("Navbar <ul> not found");
    return;
  }

  navList.innerHTML = "";
  if (authenticated && user) {
    navList.innerHTML = `
            <li><a href="#" id="profile-link">${user.email}</a></li>
            <li><a href="#" id="predict-link">Dự đoán</a></li>
            <li><a href="#" id="history-link">Lịch sử</a></li>
            <li><a href="#" id="logout-link">Đăng xuất</a></li>
        `;
  } else {
    navList.innerHTML = `
            <li><a href="#" id="login-link">Đăng nhập</a></li>
            <li><a href="#" id="register-link">Đăng ký</a></li>
        `;
  }

  // Re-attach event listeners
  const registerLink = document.getElementById("register-link");
  const loginLink = document.getElementById("login-link");
  const profileLink = document.getElementById("profile-link");
  const predictLink = document.getElementById("predict-link");
  const historyLink = document.getElementById("history-link");
  const logoutLink = document.getElementById("logout-link");

  if (registerLink) {
    registerLink.addEventListener("click", (e) => {
      e.preventDefault();
      showSection("register-form");
    });
  }
  if (loginLink) {
    loginLink.addEventListener("click", (e) => {
      e.preventDefault();
      showSection("login-form");
    });
  }
  if (profileLink) {
    profileLink.addEventListener("click", async (e) => {
      e.preventDefault();
      if ((await checkAuthStatus()).authenticated) {
        showSection("profile-form");
      }
    });
  }
  if (predictLink) {
    predictLink.addEventListener("click", async (e) => {
      e.preventDefault();
      if ((await checkAuthStatus()).authenticated) {
        showSection("predict-form");
      }
    });
  }
  if (historyLink) {
    historyLink.addEventListener("click", async (e) => {
      e.preventDefault();
      if ((await checkAuthStatus()).authenticated) {
        showSection("history-form");
        await loadHistory();
      }
    });
  }
  if (logoutLink) {
    logoutLink.addEventListener("click", (e) => {
      e.preventDefault();
      removeToken();
      showSection("login-form");
      updateNavbar();
    });
  }
}

// Registration
const registerForm = document.getElementById("register-form-element");
if (registerForm) {
  registerForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearMessages();
    showLoading();

    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;
    const confirmPassword = document.getElementById(
      "register-confirm-password"
    ).value;

    if (!email || !password || !confirmPassword) {
      showError("Vui lòng điền đầy đủ thông tin.");
      hideLoading();
      return;
    }
    if (!validateEmail(email)) {
      showError("Email không đúng định dạng.");
      hideLoading();
      return;
    }
    if (!validatePassword(password)) {
      showError(
        "Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số."
      );
      hideLoading();
      return;
    }
    if (password !== confirmPassword) {
      showError("Mật khẩu xác nhận không khớp.");
      hideLoading();
      return;
    }

    try {
      const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      hideLoading();
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Lỗi đăng ký");
      }
      showSuccess("Đăng ký thành công! Vui lòng đăng nhập.");
      setTimeout(() => showSection("login-form"), 2000);
    } catch (error) {
      showError(`Lỗi: ${error.message}`);
      hideLoading();
    }
  });
}

// Login
const loginForm = document.getElementById("login-form-element");
if (loginForm) {
  loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearMessages();
    showLoading();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    if (!email || !password) {
      showError("Vui lòng điền đầy đủ thông tin.");
      hideLoading();
      return;
    }

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      hideLoading();
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Lỗi đăng nhập");
      }
      setToken(result.access_token);
      showSuccess("Đăng nhập thành công!");
      await updateNavbar();
      showSection("predict-form");
    } catch (error) {
      showError(`Lỗi: ${error.message}`);
      hideLoading();
    }
  });
}

// Profile
const profileForm = document.getElementById("profile-form-element");
if (profileForm) {
  profileForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const { authenticated } = await checkAuthStatus();
    if (!authenticated) return;
    clearMessages();
    showLoading();

    const userData = {
      age: parseInt(document.getElementById("profile-age").value),
      sex: parseInt(document.getElementById("profile-sex").value),
      height: parseFloat(document.getElementById("profile-height").value),
      weight: parseFloat(document.getElementById("profile-weight").value),
      children: parseInt(document.getElementById("profile-children").value),
      smoker: parseInt(document.getElementById("profile-smoker").value),
      region: parseInt(document.getElementById("profile-region").value),
    };
    const bmi = calculateProfileBMI();

    if (isNaN(userData.age) || userData.age < 18 || userData.age > 64) {
      showError("Tuổi phải từ 18 đến 64.");
      hideLoading();
      return;
    }
    if (isNaN(userData.sex) || ![0, 1].includes(userData.sex)) {
      showError("Giới tính không hợp lệ.");
      hideLoading();
      return;
    }
    if (
      isNaN(userData.height) ||
      userData.height < 1.0 ||
      userData.height > 2.5
    ) {
      showError("Chiều cao phải từ 1.0 đến 2.5 mét.");
      hideLoading();
      return;
    }
    if (
      isNaN(userData.weight) ||
      userData.weight < 30 ||
      userData.weight > 150
    ) {
      showError("Cân nặng phải từ 30 đến 150 kg.");
      hideLoading();
      return;
    }
    if (!bmi || bmi < 15 || bmi > 50) {
      showError("BMI phải từ 15 đến 50.");
      hideLoading();
      return;
    }
    if (
      isNaN(userData.children) ||
      userData.children < 0 ||
      userData.children > 5
    ) {
      showError("Số con cái phải từ 0 đến 5.");
      hideLoading();
      return;
    }
    if (isNaN(userData.smoker) || ![0, 1].includes(userData.smoker)) {
      showError("Tình trạng hút thuốc không hợp lệ.");
      hideLoading();
      return;
    }
    if (isNaN(userData.region) || ![0, 1, 2, 3].includes(userData.region)) {
      showError("Khu vực không hợp lệ.");
      hideLoading();
      return;
    }

    try {
      const response = await fetch("/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(userData),
      });
      hideLoading();
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          removeToken();
          showSection("login-form");
          await updateNavbar();
          showError("Vui lòng đăng nhập lại.");
          return;
        }
        throw new Error(result.detail || "Lỗi cập nhật hồ sơ");
      }
      showSuccess("Cập nhật hồ sơ thành công.");
    } catch (error) {
      showError(`Lỗi: ${error.message}`);
      hideLoading();
    }
  });
}

// Prediction
const predictionForm = document.getElementById("prediction-form-element");
if (predictionForm) {
  predictionForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const { authenticated } = await checkAuthStatus();
    if (!authenticated) return;
    clearMessages();
    showLoading();

    try {
      const formData = new FormData(this);
      const bmi = calculateBMI();

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

      if (isNaN(data.age) || data.age < 18 || data.age > 64) {
        showError("Tuổi phải từ 18 đến 64.");
        hideLoading();
        return;
      }
      if (isNaN(data.sex) || ![0, 1].includes(data.sex)) {
        showError("Giới tính không hợp lệ.");
        hideLoading();
        return;
      }
      if (isNaN(data.height) || data.height < 1.0 || data.height > 2.5) {
        showError("Chiều cao phải từ 1.0 đến 2.5 mét.");
        hideLoading();
        return;
      }
      if (isNaN(data.weight) || data.weight < 30 || data.weight > 150) {
        showError("Cân nặng phải từ 30 đến 150 kg.");
        hideLoading();
        return;
      }
      if (!bmi || bmi < 15 || bmi > 50) {
        showError("BMI phải từ 15 đến 50.");
        hideLoading();
        return;
      }
      if (isNaN(data.children) || data.children < 0 || data.children > 5) {
        showError("Số con cái phải từ 0 đến 5.");
        hideLoading();
        return;
      }
      if (isNaN(data.smoker) || ![0, 1].includes(data.smoker)) {
        showError("Tình trạng hút thuốc không hợp lệ.");
        hideLoading();
        return;
      }
      if (isNaN(data.region) || ![0, 1, 2, 3].includes(data.region)) {
        showError("Khu vực không hợp lệ.");
        hideLoading();
        return;
      }
      if (!["random_forest", "decision_tree"].includes(data.model)) {
        showError("Mô hình không hợp lệ.");
        hideLoading();
        return;
      }

      const response = await fetch("/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(data),
      });
      hideLoading();
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          removeToken();
          showSection("login-form");
          await updateNavbar();
          showError("Vui lòng đăng nhập lại.");
          return;
        }
        let errorMsg;
        if (Array.isArray(result.detail)) {
          errorMsg = result.detail.map((e) => e.msg).join("; ");
        } else {
          errorMsg = result.detail || `Lỗi HTTP: ${response.status}`;
        }
        throw new Error(errorMsg);
      }
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
      showError(`Lỗi: ${error.message}`);
      hideLoading();
      const predictionResult = document.getElementById("prediction-result");
      if (predictionResult) predictionResult.style.display = "none";
    }
  });
}

// History
async function loadHistory() {
  const { authenticated } = await checkAuthStatus();
  if (!authenticated) return;
  clearMessages();
  try {
    const response = await fetch("/history", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${getToken()}`,
      },
    });
    const result = await response.json();
    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        showSection("login-form");
        await updateNavbar();
        showError("Vui lòng đăng nhập lại.");
        return;
      }
      throw new Error(result.detail || "Lỗi lấy lịch sử");
    }
    const historyTableBody = document.getElementById("history-table-body");
    if (historyTableBody) {
      historyTableBody.innerHTML = "";
      if (result.length === 0) {
        historyTableBody.innerHTML =
          '<tr><td colspan="3" class="text-center">Chưa có lịch sử dự đoán nào.</td></tr>';
        return;
      }
      result.forEach((item) => {
        const inputData = item.input_data;
        const historyRow = document.createElement("tr");
        historyRow.innerHTML = `
                    <td>${item.timestamp}</td>
                    <td>Tuổi: ${inputData.age}, Giới tính: ${
          inputData.sex === 0 ? "Nam" : "Nữ"
        }, 
                        Chiều cao: ${inputData.height}m, Cân nặng: ${
          inputData.weight
        }kg, 
                        Số con: ${inputData.children}, Hút thuốc: ${
          inputData.smoker === 1 ? "Có" : "Không"
        }, 
                        Khu vực: ${
                          ["Southwest", "Southeast", "Northwest", "Northeast"][
                            inputData.region
                          ]
                        }</td>
                    <td>${item.prediction.toLocaleString("vi-VN")}</td>
                `;
        historyTableBody.appendChild(historyRow);
      });
    }
  } catch (error) {
    showError(`Lỗi: ${error.message}`);
    console.error("Load history error:", error);
  }
}

// Navigation
document.addEventListener("DOMContentLoaded", async function () {
  await updateNavbar();
});
