# PHIVOLCS Earthquake Tweet Scraper

This project is a Python-based web scraper that extracts recent earthquake-related tweets from the official PHIVOLCS-DOST Twitter/X account. It automates browser interactions using Selenium and parses tweet content using regular expressions to extract key earthquake details such as magnitude, depth, location, intensity, and date/time.

---

## 🚧 Project Status

🛠 **This is an ongoing personal project.**  
Improvements are continuously being made to enhance scraping reliability, data cleaning accuracy, and integration with real-time monitoring or databases. Contributions and suggestions are welcome!

---

## 🎯 Purpose

This project aims to provide a tool for **earthquake data collection and analysis** from public social media sources. By extracting and structuring real-time tweets from PHIVOLCS, the project supports:

- Early situational awareness and communication
- Data analysis and visualization of earthquake trends
- Supplementing official seismic datasets with social media data

---

## 🙋 Who Can Use This Script

This tool is suitable for:

- **Students and researchers** studying earthquake hazards, disaster response, or social media data mining
- **Data analysts and developers** looking to explore real-time scraping and NLP from X (formerly Twitter)
- **Emergency communication teams** interested in enhancing their situational dashboards or alerts (with proper compliance)

Please ensure you use it **for educational, research, or non-commercial purposes**, and **comply with the terms of use of the data sources**, particularly Twitter/X.

---

## 🚀 Features

- **Headless scraping** using Selenium WebDriver and Chrome
- **Robust parsing** of tweet content using regex
- **Smart scrolling** to load older tweets dynamically
- **Structured data extraction** to CSV (both raw and cleaned formats)
- Detects and filters **earthquake-related content** only
- Generates **timestamped files** to prevent overwrites

---

## 📦 Requirements

- Python 3.7+
- Google Chrome (latest)
- ChromeDriver (auto-managed by `webdriver-manager`)

