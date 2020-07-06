from flask import Flask, request
import requests
import random
import json
import os
from twilio.twiml.messaging_response import MessagingResponse

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# set NYTimes API key (delete if changing app)
books_api = os.environ.get("KEY")

country_codes = ['DZ','AO','BJ','BW','BF','BI','CM','CV','CF','TD','KM','CG','CD','DJ','EG','GQ','ER','ET','GA','GM','GH','GN','GW','CI','KE','LS','LR','LY','MG','MW','ML','MR','MU','YT','MA','MZ','NA','NE','NG','RE','RW','SH','ST','SN','SC','SL','SO','ZA','SS','SD','SZ','TZ','TG','TN','UG','EH','ZM','ZW']

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower()
    resp = MessagingResponse()
    msg = resp.message()
    responded = False
    incoming_num = request.values.get('From', '')
    number = incoming_num.strip('whatsapp:')
    
    #is there a better way to access the column values without having to go and check which row number it is???
    exists = db.execute("SELECT * from users WHERE phone = :phone", {'phone': number}).fetchall()
    if exists:
        username = exists[0][1]
        current_country = exists[0][5]
        print(current_country)
        user_id = exists[0][0]
        score = exists[0][7]

        #get current game info
        #games = db.execute("SELECT * from users WHERE phone = :phone", {'phone': number}).fetchall()
        #current_game = games[0][6]

        #db.execute("SELECT * from games WHERE phone = :phone", {'phone': number}).fetchall()
            
        if username is None:
            db.execute("UPDATE users SET name = :name WHERE phone = :number", {'name': incoming_msg, 'number': number})
            db.commit()
            msg.body(f'Thank you {incoming_msg}! To start your quiz, send "begin"\n\nWhen you want to leave the game, please send "exit game".\n\nRemember: spelling, accents, and hyphens count! Good luck!')
            responded = True
        
        elif 'begin' in incoming_msg:
            country = random_country(number)
            msg.body("What is the capital of {}?".format(country))
            responded = True

        elif 'exit game' in incoming_msg:
            db.execute("UPDATE users SET score = 0, current_country = NULL WHERE phone = :number", {'number': number})
            db.commit()
            msg.body(f"Thanks for playing! Your score for this game is {score}. \n\nSend 'begin' when you want to play again!\n\nOr, visit this link to test your knowledge of African countries: https://codepen.io/ktich/full/ExVmYGr")
            responded = True
        
        elif current_country is not None:
            country = random_country(number)
            if check(current_country, incoming_msg):
                increase_score(number, score)
                msg.body(f"Correct! \n\nWhat is the capital of: {country}")
            else:
                correct_answer = check(current_country, incoming_msg)
                msg.body(f"Incorrect! \nThe answer is {correct_answer}.\n\nWhat is the capital of: {country}")
            responded = True
    
    if not exists:
        db.execute("INSERT INTO users (phone) VALUES (:phone)", {'phone': number})
        db.commit()
        msg.body("Hello! Welcome to the Capital Cities Africa quiz! What's your name?")
        responded = True

    if not responded:
        msg.body('I only know about things in the menu, sorry!')
    return str(resp)

def random_country(number):
    country_code = random.choice(country_codes)
    db.execute("UPDATE users SET current_country = :country WHERE phone = :number", {'country': country_code, 'number': number})
    db.commit()
    r = requests.get(f'https://restcountries.eu/rest/v2/alpha/{country_code}')
    info = json.loads(r.text)
    country = info['name']
    return country

def check(country, response):
    r = requests.get(f'https://restcountries.eu/rest/v2/alpha/{country}')
    info = json.loads(r.text)
    capital = info['capital'].lower()
    print(capital)
    if response==capital:
        return capital, True
    else:
        return False

def increase_score(number, score):
    score = score + 1
    db.execute("UPDATE users SET score = :score WHERE phone = :number", {'score': score, 'number': number})
    db.commit()

if __name__ == '__main__':
    app.run()