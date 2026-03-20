# 🏃‍♂️ Trainitz

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Trainitz** is a lightweight Python library designed to handle training and sports metrics with ease. It provides specialized classes for managing complex measurements like **Time** (durations) and **Distance**, including arithmetic operations and robust string parsing.

---

## 🚀 Key Features

- **Precision Time Handling**: Arithmetic operations (add, sub, mul, div) with durations, supporting hours, minutes, seconds, and milliseconds.
- **Distance Measurements**: Seamless conversions between meters and kilometers, with support for unit parsing.
- **Robust Parsing**: Built-in regex-based readers to convert strings (e.g., `"1:20:30"`, `"5km"`, `"400m"`) directly into Python objects.
- **Type-Safe Comparisons**: Fully compatible with Python's comparison operators (`<`, `<=`, `>`, `>=`, `==`).

---

## 📦 Installation

To install the current version for development:

```bash
git clone https://github.com/artitzco/trainitz.git
cd trainitz
pip install -e .
```

---

## 🛠 Usage Examples

### ⏱ Time Handling
```python
from trainitz.metrics import Time

t1 = Time("1:20:30")
t2 = Time(minutes=45)
total = t1 + t2
print(total) # Outputs human-readable format
```

### 🛣 Distance Handling
```python
from trainitz.metrics import Distance

d1 = Distance("10km")
d2 = Distance(meters=500)
print(d1 + d2) # 10.5km
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue for suggestions and bug reports.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
Created by [artitzco](https://github.com/artitzco)
