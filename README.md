# 💸 Subscription Slayer

Subscription Slayer is a full-stack web application designed to help users track, manage, and analyze their recurring subscriptions to save money. It is built with a Python Flask backend and a dynamic, modern frontend using Bootstrap and Three.js.



## Key Features

- **Full User Authentication**: Secure registration and login system to manage private subscription lists.
- **CRUD Functionality**: Users can Create, Read, Update, and Delete their subscriptions with details like cost, billing frequency, and category.
- **Interactive Dashboard**: A central hub that displays all subscriptions and key financial data, including:
    - Total monthly cost calculation.
    - An alert panel for payments due within the next 14 days.
    - A doughnut chart visualizing spending by category.
- **Smart Value Score**: An algorithm calculates a "value score" for each subscription based on its cost and usage frequency, helping users identify which services are worth keeping.
- **Smart Recommendations**: Automatically flags subscriptions with a poor value score and shows potential monthly savings.
- **Modern 3D Frontend**: The landing and authentication pages feature an engaging 3D animated background built with Three.js for a memorable user experience.

---
## Tech Stack

- **Backend**: Python, Flask, Flask-SQLAlchemy, Flask-Login
- **Database**: SQLite (with Flask-Migrate for migrations)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Visualization**: Chart.js, Three.js

---
## How to Run This Project

1.  Clone the repository to your local machine.
2.  Navigate into the project directory.
3.  Create and activate a virtual environment:
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    py -m venv venv
    venv\Scripts\activate
    ```
4.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
5.  Initialize and upgrade the database:
    ```bash
    flask db init
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```
6.  Run the application:
    ```bash
    flask run
    ```
7.  Open your browser and go to `http://127.0.0.1:5000`.
