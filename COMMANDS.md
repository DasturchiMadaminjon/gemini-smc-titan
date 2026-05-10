# 🚀 TITAN V27.2 MASTER ENGINE: BUYRUQLAR RO'YXATI

Ushbu faylda loyihani turli muhitlarda (Windows, AWS, PythonAnywhere) boshqarish uchun barcha zarur buyruqlar jamlangan.

---

## 💻 1. WINDOWS (Lokal muhit)

### Asosiy buyruqlar:
*   **Botni ishga tushirish**:
    ```powershell
    python bot.py
    ```
*   **Bilimlar bazasini indeksatsiya qilish (RAG)**:
    ```powershell
    python build_vectors.py
    ```
*   **Watchdog (Avto-restart) orqali ishga tushirish**:
    ```powershell
    python watchdog.py
    ```

### TDD Testlarni yurgizish:
*   **Barcha testlarni yurgizish**:
    ```powershell
    pytest tests -v
    ```
*   **Faqat AI modullini testlash**:
    ```powershell
    pytest tests/test_ai_engine.py -v
    ```
*   **Tugmalar va menyularni testlash**:
    ```powershell
    pytest tests/test_all_buttons_tdd.py -v
    ```

---

## ☁️ 2. AWS EC2 (Linux/Ubuntu)

### Tayyorgarlik:
```bash
chmod +x setup.sh
./setup.sh
```

### Fon rejimida ishga tushirish (PM2 orqali):
*   **Botni boshlash**:
    ```bash
    pm2 start bot.py --name "titan-bot" --interpreter python3
    ```
*   **Loglarni ko'rish**:
    ```bash
    pm2 logs titan-bot
    ```

---

## 🐍 3. PYTHONANYWHERE (PA)

### Ishga tushirish (Task qismiga):
```bash
python3 /home/USERNAME/PROJECT_NAME/bot.py
```

---

## 🛠 4. QO'SHIMCHA
*   **Kutubxonalarni yangilash**: `pip install -r requirements.txt --upgrade`
