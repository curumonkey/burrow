in termux,
install python venv
apt install python3

uvicorn burrow.app.main:app --host 0.0.0.0 --port 8000 --reload
