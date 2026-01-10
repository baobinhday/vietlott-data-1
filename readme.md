# 🎰 Vietlott Data

[![GitHub Actions](https://github.com/vietvudanh/vietlott-data/workflows/crawl/badge.svg)](https://github.com/vietvudanh/vietlott-data/actions)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Data Updated](https://img.shields.io/badge/data-daily%20updated-brightgreen.svg)](https://github.com/vietvudanh/vietlott-data/commits/main)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Deployed-blue)](https://vietvudanh.github.io/vietlott-data/)

> 📊 **Automated Vietnamese Lottery Data Collection & Analysis**
>
> This project automatically crawls and analyzes Vietnamese lottery data from [vietlott.vn](https://vietlott.vn/), providing comprehensive statistics and insights for all major lottery products.

## 🎯 Supported Lottery Products

| Product | Link | Description |
|---------|------|-------------|
| **Power 6/55** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655) | Choose 6 numbers from 1-55 |
| **Power 6/45** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645) | Choose 6 numbers from 1-45 |
| **Power 5/35** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535) | Choose 5 numbers from 1-35 |
| **Keno** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-keno) | Fast-pace number game |
| **Max 3D** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3d) | 3-digit lottery game |
| **Max 3D Pro** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3dpro) | Enhanced 3D lottery |
| **Bingo18** | [🔗 Results](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18) | 3 numbers from 0-9 game |


## 📋 Table of Contents

- [🎯 Supported Lottery Products](#-supported-lottery-products)
- [Predictions](#-predictions)
- [📊 Data Statistics](#-data-statistics)
- [📈 Power 6/55 Analysis](#-power-655-analysis)
  - [📅 Recent Results](#-recent-results)
  - [🎲 Number Frequency (All Time)](#-number-frequency-all-time)
  - [📊 Frequency Analysis by Period](#-frequency-analysis-by-period)
- [⚙️ How It Works](#️-how-it-works)
- [🚀 Installation & Usage](#-installation--usage)
- [📄 License](#-license)


## Predictions

Predicitons models are at [/src/predictions](./src/machine_learning/prediction_summary.md)

## 📊 Data Statistics

| Product | Total Draws | Start Date | End Date | Total Records | First ID | Latest ID |
| --- | --- | --- | --- | --- | --- | --- |
| Power 655 | 1293 | 2017-08-01 | 2026-01-10 | 1293 | 00001 | 01293 |
| Power 645 | 1259 | 2017-10-25 | 2026-01-09 | 1259 | 00198 | 01456 |
| Power 535 | 160 | 2025-06-29 | 2026-01-10 | 320 | 00001 | 00392 |
| Keno | 411 | 2022-12-04 | 2026-01-10 | 52875 | #0110271 | #0266346 |
| 3D | 1023 | 2019-04-22 | 2026-01-09 | 1023 | 00001 | 01027 |
| 3D Pro | 670 | 2021-09-14 | 2026-01-10 | 670 | 00001 | 00674 |
| Bingo18 | 386 | 2024-12-03 | 2026-01-10 | 52836 | 0083123 | 0147257 |

## 📈 Power 6/55 Analysis

### 📅 Recent Results (Last 10 draws)
| date | id | result | process_time |
| --- | --- | --- | --- |
| 2026-01-10 | 01293 | [9, 16, 30, 33, 34, 38, 49] | 2026-01-10T22:55:42.656288 |
| 2026-01-08 | 01292 | [20, 22, 36, 43, 45, 50, 47] | 2026-01-10T22:55:42.656854 |
| 2026-01-06 | 01291 | [22, 28, 29, 30, 34, 47, 20] | 2026-01-10T22:55:42.657154 |
| 2026-01-03 | 01290 | [10, 16, 17, 23, 33, 36, 42] | 2026-01-10T22:55:42.657424 |
| 2026-01-01 | 01289 | [5, 16, 29, 33, 39, 42, 54] | 2026-01-10T22:55:42.657780 |
| 2025-12-30 | 01288 | [11, 30, 35, 41, 48, 55, 38] | 2026-01-10T22:55:42.658288 |
| 2025-12-27 | 01287 | [16, 21, 30, 37, 39, 40, 13] | 2026-01-10T22:55:42.658514 |
| 2025-12-25 | 01286 | [4, 6, 32, 37, 40, 48, 38] | 2026-01-10T22:55:42.658726 |
| 2025-12-23 | 01285 | [2, 10, 16, 25, 32, 38, 3] | 2026-01-10T22:55:42.673010 |
| 2025-12-20 | 01284 | [22, 32, 33, 35, 40, 41, 23] | 2025-12-21T00:00:50.783917 |

### 🎲 Number Frequency (All Time)
| result | count | % | -1 | 1result | 1count | 1% | -2 | 2result | 2count | 2% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 173 | 1.91 |  | 21 | 158 | 1.75 |  | 41 | 192 | 2.12 |
| 2 | 149 | 1.65 |  | 22 | 188 | 2.08 |  | 42 | 170 | 1.88 |
| 3 | 175 | 1.93 |  | 23 | 176 | 1.94 |  | 43 | 186 | 2.06 |
| 4 | 136 | 1.5 |  | 24 | 167 | 1.85 |  | 44 | 170 | 1.88 |
| 5 | 166 | 1.83 |  | 25 | 144 | 1.59 |  | 45 | 165 | 1.82 |
| 6 | 139 | 1.54 |  | 26 | 150 | 1.66 |  | 46 | 168 | 1.86 |
| 7 | 141 | 1.56 |  | 27 | 152 | 1.68 |  | 47 | 165 | 1.82 |
| 8 | 177 | 1.96 |  | 28 | 144 | 1.59 |  | 48 | 176 | 1.94 |
| 9 | 181 | 2.0 |  | 29 | 175 | 1.93 |  | 49 | 165 | 1.82 |
| 10 | 156 | 1.72 |  | 30 | 150 | 1.66 |  | 50 | 164 | 1.81 |
| 11 | 170 | 1.88 |  | 31 | 173 | 1.91 |  | 51 | 184 | 2.03 |
| 12 | 172 | 1.9 |  | 32 | 169 | 1.87 |  | 52 | 168 | 1.86 |
| 13 | 157 | 1.73 |  | 33 | 168 | 1.86 |  | 53 | 170 | 1.88 |
| 14 | 165 | 1.82 |  | 34 | 185 | 2.04 |  | 54 | 154 | 1.7 |
| 15 | 153 | 1.69 |  | 35 | 162 | 1.79 |  | 55 | 163 | 1.8 |
| 16 | 158 | 1.75 |  | 36 | 156 | 1.72 |  |  |  |  |
| 17 | 149 | 1.65 |  | 37 | 150 | 1.66 |  |  |  |  |
| 18 | 166 | 1.83 |  | 38 | 160 | 1.77 |  |  |  |  |
| 19 | 166 | 1.83 |  | 39 | 156 | 1.72 |  |  |  |  |
| 20 | 177 | 1.96 |  | 40 | 181 | 2.0 |  |  |  |  |

### 📊 Frequency Analysis by Period

#### Last 30 Days
| result | count | % | -1 | 1result | 1count | 1% | -2 | 2result | 2count | 2% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 1.02 |  | 25 | 1 | 1.02 |  | 49 | 1 | 1.02 |
| 3 | 1 | 1.02 |  | 28 | 1 | 1.02 |  | 50 | 2 | 2.04 |
| 4 | 1 | 1.02 |  | 29 | 3 | 3.06 |  | 52 | 2 | 2.04 |
| 5 | 2 | 2.04 |  | 30 | 5 | 5.1 |  | 54 | 1 | 1.02 |
| 6 | 1 | 1.02 |  | 32 | 3 | 3.06 |  | 55 | 4 | 4.08 |
| 7 | 1 | 1.02 |  | 33 | 4 | 4.08 |  |  |  |  |
| 8 | 1 | 1.02 |  | 34 | 2 | 2.04 |  |  |  |  |
| 9 | 2 | 2.04 |  | 35 | 2 | 2.04 |  |  |  |  |
| 10 | 2 | 2.04 |  | 36 | 3 | 3.06 |  |  |  |  |
| 11 | 1 | 1.02 |  | 37 | 3 | 3.06 |  |  |  |  |
| 12 | 2 | 2.04 |  | 38 | 7 | 7.14 |  |  |  |  |
| 13 | 2 | 2.04 |  | 39 | 3 | 3.06 |  |  |  |  |
| 14 | 1 | 1.02 |  | 40 | 3 | 3.06 |  |  |  |  |
| 16 | 5 | 5.1 |  | 41 | 2 | 2.04 |  |  |  |  |
| 17 | 1 | 1.02 |  | 42 | 2 | 2.04 |  |  |  |  |
| 18 | 1 | 1.02 |  | 43 | 1 | 1.02 |  |  |  |  |
| 20 | 3 | 3.06 |  | 45 | 2 | 2.04 |  |  |  |  |
| 21 | 2 | 2.04 |  | 46 | 1 | 1.02 |  |  |  |  |
| 22 | 3 | 3.06 |  | 47 | 2 | 2.04 |  |  |  |  |
| 23 | 2 | 2.04 |  | 48 | 3 | 3.06 |  |  |  |  |

#### Last 60 Days
| result | count | % | -1 | 1result | 1count | 1% | -2 | 2result | 2count | 2% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0.53 |  | 21 | 3 | 1.59 |  | 41 | 3 | 1.59 |
| 2 | 2 | 1.06 |  | 22 | 4 | 2.12 |  | 42 | 6 | 3.17 |
| 3 | 2 | 1.06 |  | 23 | 3 | 1.59 |  | 43 | 3 | 1.59 |
| 4 | 4 | 2.12 |  | 24 | 2 | 1.06 |  | 44 | 1 | 0.53 |
| 5 | 4 | 2.12 |  | 25 | 1 | 0.53 |  | 45 | 3 | 1.59 |
| 6 | 1 | 0.53 |  | 26 | 2 | 1.06 |  | 46 | 3 | 1.59 |
| 7 | 2 | 1.06 |  | 27 | 2 | 1.06 |  | 47 | 3 | 1.59 |
| 8 | 2 | 1.06 |  | 28 | 3 | 1.59 |  | 48 | 5 | 2.65 |
| 9 | 3 | 1.59 |  | 29 | 5 | 2.65 |  | 49 | 2 | 1.06 |
| 10 | 6 | 3.17 |  | 30 | 8 | 4.23 |  | 50 | 3 | 1.59 |
| 11 | 3 | 1.59 |  | 31 | 4 | 2.12 |  | 51 | 1 | 0.53 |
| 12 | 5 | 2.65 |  | 32 | 5 | 2.65 |  | 52 | 3 | 1.59 |
| 13 | 4 | 2.12 |  | 33 | 6 | 3.17 |  | 53 | 1 | 0.53 |
| 14 | 4 | 2.12 |  | 34 | 4 | 2.12 |  | 54 | 4 | 2.12 |
| 15 | 2 | 1.06 |  | 35 | 4 | 2.12 |  | 55 | 4 | 2.12 |
| 16 | 6 | 3.17 |  | 36 | 4 | 2.12 |  |  |  |  |
| 17 | 1 | 0.53 |  | 37 | 4 | 2.12 |  |  |  |  |
| 18 | 2 | 1.06 |  | 38 | 9 | 4.76 |  |  |  |  |
| 19 | 2 | 1.06 |  | 39 | 3 | 1.59 |  |  |  |  |
| 20 | 7 | 3.7 |  | 40 | 5 | 2.65 |  |  |  |  |

#### Last 90 Days
| result | count | % | -1 | 1result | 1count | 1% | -2 | 2result | 2count | 2% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0.37 |  | 21 | 5 | 1.83 |  | 41 | 5 | 1.83 |
| 2 | 2 | 0.73 |  | 22 | 7 | 2.56 |  | 42 | 6 | 2.2 |
| 3 | 4 | 1.47 |  | 23 | 4 | 1.47 |  | 43 | 5 | 1.83 |
| 4 | 4 | 1.47 |  | 24 | 4 | 1.47 |  | 44 | 2 | 0.73 |
| 5 | 6 | 2.2 |  | 25 | 2 | 0.73 |  | 45 | 5 | 1.83 |
| 6 | 3 | 1.1 |  | 26 | 4 | 1.47 |  | 46 | 3 | 1.1 |
| 7 | 3 | 1.1 |  | 27 | 6 | 2.2 |  | 47 | 4 | 1.47 |
| 8 | 6 | 2.2 |  | 28 | 4 | 1.47 |  | 48 | 6 | 2.2 |
| 9 | 5 | 1.83 |  | 29 | 8 | 2.93 |  | 49 | 4 | 1.47 |
| 10 | 8 | 2.93 |  | 30 | 8 | 2.93 |  | 50 | 5 | 1.83 |
| 11 | 6 | 2.2 |  | 31 | 6 | 2.2 |  | 51 | 1 | 0.37 |
| 12 | 7 | 2.56 |  | 32 | 5 | 1.83 |  | 52 | 3 | 1.1 |
| 13 | 5 | 1.83 |  | 33 | 8 | 2.93 |  | 53 | 1 | 0.37 |
| 14 | 7 | 2.56 |  | 34 | 4 | 1.47 |  | 54 | 5 | 1.83 |
| 15 | 4 | 1.47 |  | 35 | 5 | 1.83 |  | 55 | 6 | 2.2 |
| 16 | 10 | 3.66 |  | 36 | 7 | 2.56 |  |  |  |  |
| 17 | 1 | 0.37 |  | 37 | 6 | 2.2 |  |  |  |  |
| 18 | 3 | 1.1 |  | 38 | 11 | 4.03 |  |  |  |  |
| 19 | 4 | 1.47 |  | 39 | 3 | 1.1 |  |  |  |  |
| 20 | 9 | 3.3 |  | 40 | 7 | 2.56 |  |  |  |  |



## ⚙️ How It Works

### 🤖 Automated Data Collection

This project runs completely automatically using **GitHub Actions** - no server required!

- **⏰ Schedule**: Runs daily via [GitHub Actions workflow](.github/workflows/crawl.yaml)
- **🔄 Process**: Fetches latest results → Processes data → Commits to repository
- **📊 Analysis**: Generates statistics and updates README automatically

### 🕵️ Data Crawling Method

The data collection works by:
1. **🔍 Network Analysis**: Inspecting browser-server communication
2. **🐍 Python Replication**: Recreating the data fetch logic in Python
3. **📋 Structured Storage**: Saving results in JSONL format for easy analysis
4. **🔄 Continuous Updates**: Daily automated runs ensure fresh data

> **Note**: This is purely for educational and research purposes. No gambling advice is provided.


## 🚀 Installation & Usage

### 📦 Install via pip

```bash
pip install -i vietlott-data
```

### 💻 Command Line Interface

#### 🔍 Crawl Data

```bash
vietlott-crawl [OPTIONS] PRODUCT

# Options:
#   --run-date TEXT       Specific date to crawl (default: current date)
#   --index-from INTEGER  Starting page index (default: 0)
#   --index-to INTEGER    Ending page index (default: None)
#   --help               Show help message
```

#### 🔧 Backfill Missing Data

```bash
vietlott-missing [OPTIONS] PRODUCT

# Options:
#   --limit INTEGER  Number of pages to process (default: 20)
#   --help          Show help message
```

> **Available Products**: power_655, power_645, power_535, keno, 3d, 3d_pro, bingo18

### 🛠️ Development Setup

```bash
# Clone the repository
git clone https://github.com/vietvudanh/vietlott-data.git ; cd vietlott-data

# Install dependencies (recommend using uv and virtual environment)
uv sync --dev

# Run tests
uv run pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <strong>⭐ If you find this project useful, please consider giving it a star!</strong>
</div>

