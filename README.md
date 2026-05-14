### Запуск приложения
#### Настройка backend части:
1. В терминале последовательно выполните данные файлы
cd backend

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

2. Скопируйте и отредактируйте файл .env.example, выполнив следующие команды и указав подключение к бд
cd..

cp .env.example backend/.env

3. Запустите приложение
cd backend

uvicorn app.main:app --reload


#### Настройка frontend части:
1. Открыть новый терминал, не закрывая старый

2. Введите последовательно 
cd frontend

npm install

npm run dev

3. Перейдите по указанной в терминале ссылке
