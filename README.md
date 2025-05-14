# Heroku Python App

This project is a Python application designed to be deployed on Heroku. It includes the necessary files and configurations to run a web application.

## Project Structure

```
heroku-python-app
├── app
│   ├── __init__.py
│   ├── main.py
│   └── requirements.txt
├── Procfile
├── runtime.txt
├── .gitignore
└── README.md
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone https://github.com/yourusername/heroku-python-app.git
   cd heroku-python-app
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r app/requirements.txt
   ```

4. **Run the application locally:**
   ```
   python app/main.py
   ```

## Deployment to Heroku

1. **Login to Heroku:**
   ```
   heroku login
   ```

2. **Create a new Heroku app:**
   ```
   heroku create your-app-name
   ```

3. **Deploy the application:**
   ```
   git add .
   git commit -m "Initial commit"
   git push heroku master
   ```

4. **Open the application in your browser:**
   ```
   heroku open
   ```

## Usage

After deploying, you can access your application at `https://your-app-name.herokuapp.com`.

## License

This project is licensed under the MIT License.