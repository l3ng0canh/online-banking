#!/usr/bin/python
from flask import Flask, request, jsonify
from flaskext.mysql import MySQL
from decimal import Decimal
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import pyotp
import os
import re
import html

app = Flask(__name__)

mysql = MySQL()

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'bank'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)


def Response(status, message, data={}):
    return jsonify(
        {
            "status": status,
            "message": message,
            "data": data
        }
    )



# code API
@app.route("/")
def index():
    return "Hihi"

# chuyen tien
# name1, name2, accountNumber1, accountNumber2, amount

@app.route("/transfer", methods=["POST"])
def tranfer():

    try:
        data = request.get_json()
        sender = data["sender"]
        receiver = data["receiver"]
        amount = data["amount"]

        if sender == receiver:
            return Response(0, "Invalid query parameters")
        # for param in [sender, receiver]:
        #     if not bool(re.match("^[A-Za-z0-9_%]*$", param)):
        #         return Response(0, "Invalid query parameters")
                
        description = html.escape(re.escape(data["description"]))
        #fullname = data["fullname"]
    except:
        return Response(0, "Invalid query parameters")

    # check amount to tranfer
    if amount < 100:
        return Response(0, "The minimum amount to transfer is 100")

    # init connection
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    # get current amount of sender's money
    try:
        query = """SELECT * FROM primary_account WHERE account_number=%s"""
        inputdata = (sender)
        cursor.execute(query, inputdata)
        conn.commit()
        data = cursor.fetchall()

        if len(data) == 0:
            return Response(0, "Something went wrong, please try later")
        else:
            sender_money = data[0][1]

        conn.commit()
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    # get current amount of receiver's money
    try:
        query = """SELECT * FROM primary_account WHERE account_number=%s"""
        inputdata = (receiver)
        cursor.execute(query, inputdata)
        conn.commit()
        data = cursor.fetchall()

        if len(data) == 0:
            return Response(0, "Something went wrong, please try later")
        else:
            receiver_money = data[0][1]
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    # Cong tru tien trong tai khoan cua sender and receiver
    amount = Decimal(amount)
    sender_money = sender_money - amount
    receiver_money = receiver_money + amount

    if sender_money <= Decimal(100):
        return Response(0, "Not enough money to transfer")

    # ghi data vao primary_account sender and receiver
    try:
        query = """UPDATE primary_account SET account_balance=%s WHERE account_number=%s"""
        data_tuple = (sender_money, sender)
        cursor.execute(query, data_tuple)

        query = """UPDATE primary_account SET account_balance=%s WHERE account_number=%s"""
        data_tuple = (receiver_money, receiver)
        cursor.execute(query, data_tuple)

        conn.commit()
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    # get number of rows
    try:
        cursor.execute("SELECT id FROM primary_transaction ORDER BY id DESC LIMIT 1")
        conn.commit()
        size = cursor.fetchall()[0][0]
    except:
        return Response(0, "Something went wrong, please try later")

    # lay ra primary_account_id
    try:
        query = """SELECT id FROM primary_account WHERE account_number=%s"""
        inputData = (sender)
        cursor.execute(query, inputData)
        primary_account_id = cursor.fetchall()[0][0]
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    # Them thong tin mot giao dich moi vao bang primary_transaction
    try:
        query = """INSERT INTO primary_transaction (id, amount, available_balance, date, description, status, type, primary_account_id) VALUE (%s,%s,%s,%s,%s,%s,%s, %s)"""
        data_tuple = (size + 1, amount, sender_money, time.strftime(
            '%Y-%m-%d %H:%M:%S'), description, "Finished", "Normal", primary_account_id)
        cursor.execute(query, data_tuple)
        conn.commit()
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    return Response(1, "Success")


# tra ve thong tin nguoi dung
# username, firstname, lastname, accountNumber, phone, email, userid,
@app.route("/info", methods=["POST"])
def info():

    # get parameter
    try:
        username = request.get_json()["username"]
        for param in [username]:
            if not bool(re.match("^[A-Za-z0-9_%]*$", param)):
                return Response(0, "Invalid query parameters")
    except:
        return Response(0, "Invalid query parameter")

    # init connection
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
    except:
        return Response(0, "Something went wrong, please try later")

    # get info
    try:
        query = """SELECT user_id, email, first_name, last_name, phone, username, account_number FROM user, primary_account WHERE user.primary_account_id=primary_account.id AND user.username=%s"""
        inputData = (username)
        cursor.execute(query, inputData)
        data = cursor.fetchall()

        if len(data) == 0:
            conn.commit()
            return Response(0, "Something went wrong, please try later")

        data = data[0]
        userinfo = {
            "user_id": data[0],
            "email": data[1],
            "firstName": data[2],
            "lastName": data[3],
            "phone": data[4],
            "username": data[5],
            "accountNumber": data[6]
        }
    except Exception as e:
        print(e)
        return Response(0, "Something went wrong, please try later")

    return Response(1, "Success", userinfo)


@app.route("/notify", methods = ["POST"])
def notify():
    return Response(1, "Success", {})

@app.route("/otp", methods=["POST"])
def otp():

    try:
        otpid = pyotp.random_base32()
        otp = {
            "otpid" : otpid
        }   
    except:
        return Response(0, "Something went wrong, please try later")
    
    return Response(1, "Success", otp)

@app.route("/verifyotp", methods=["POST"])
def verifyotp():
    # verify OTP, khong can lam nen return true luon
    return Response(1, "Success", {})

@app.after_request
def after_request(response):  
    timestamp = time.strftime('[%Y-%b-%d %H:%M:%S %p]')
    logger.error('%s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s', timestamp, request.remote_addr.replace(".99.", ".40."), request.method, request.scheme, str(len(request.get_data(parse_form_data=True))),  request.path,
                 response.status, json.dumps(request.args), json.dumps(request.json), request.headers.get('User-Agent'), request.headers.get('Referer'), response.get_json())
    return response


@app.errorhandler(Exception)
def exceptions(e):
    timestamp = time.strftime('[%Y-%b-%d %H:%M:%S %p]')
    logger.error('%s - %s - %s - %s - 5xx INTERNAL SERVER ERROR\n%s', timestamp,
                 request.remote_addr, request.method, request.scheme, request.full_path)
    return e.status_code


if __name__ == "__main__":
    # ghi log
    handler = RotatingFileHandler(
            'internalAPI.log', maxBytes=100000000, backupCount=3)
    logger = logging.getLogger('tdm')
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    app.run(host="0.0.0.0", port=8000)
