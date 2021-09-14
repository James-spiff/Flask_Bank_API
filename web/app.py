from flask import Flask, jsonify, request 
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt 


app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankApi 
users = db["Users"] 

def user_exists(username):
	if users.find({"Username": username}).count() == 0:
		return False
	else:
		return True 


class Register(Resource):

	def post(self):
		postedData = request.get_json()
		username = postedData['username']
		password = postedData['password']

		if user_exists(username):
			retJson = {
				"status": 301,
				"msg": "Invalid Username"
			}
			return jsonify(retJson)

		hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
		users.insert_one({
			"Username": username,
			"Password": hashed_pw,
			"Current_balance": 0,
			"Debt": 0
			})
		retJson = {
			"status": 200,
			"msg": "Registration successful"
		}
		return jsonify(retJson)

def check_balance(username):
	balance = users.find({"Username": username})[0]["Current_balance"]
	return balance

def check_debt(username):
	debt = users.find({"Username": username})[0]["Debt"]
	return debt

def generate_return_dictionary(status, msg):
	retJson = {
		"status": status,
		"msg": msg
	}
	return retJson


def verify_cred(username, password):
	if not user_exists(username):
		return False 

	hashed_pw = users.find({"Username": username})[0]["Password"]
	if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
		return True
	else:
		return False 


def verify_cred_with_msg(username, password): #This uses the function above and generates the returned JSON response
	if not user_exists(username):
		return generate_return_dictionary(301, "Invalid Username"), True 

	if not verify_cred(username, password):
		return generate_return_dictionary(302, "Invalid Credentials"), True 
	else:
		return None, False


def update_balance(username, balance):
	users.update_one({
		"Username": username
		}, {
			"$set": {
				"Current_balance": balance 
			}
		})


def update_debt(username, balance):
	users.update_one({
		"Username": username
		}, {
			"$set": {
				"Debt": balance
			}
		})


class Credit(Resource):

	def post(self):
		postedData = request.get_json()
		username = postedData['username']
		password = postedData['password']
		amount = postedData['amount']

		retJson, error = verify_cred_with_msg(username, password)

		if error:
			return jsonify(retJson)

		if amount <= 0:
			return jsonify(generate_return_dictionary(304, "Invalid amount. Amount entered must be more than 0"))

		balance = check_balance(username)
		amount -= 1 #deducts one dollar from the user for every transaction
		bank_amount = check_balance("BANK") #This checks the banks own personal account which accepts the transaction fees 
		update_balance("BANK", bank_amount + 1)
		update_balance(username, balance + amount) #updates the users account with the cash credited 

		return jsonify(generate_return_dictionary(200, "Credit transaction successful"))


class Tranfer(Resource):

	def post(self):
		postedData = request.get_json()
		username = postedData['username']
		password = postedData['password']
		receiver = postedData['receiver']
		amount = postedData['amount']

		retJson, error = verify_cred_with_msg(username, password)
		if error:
			return jsonify(retJson)

		balance = check_balance(username)
		if balance <= 0 or amount > balance:
			return jsonify(generate_return_dictionary(304, "Insufficient Funds"))

		if not user_exists(receiver): #checks if the receiver has a registered account 
			return jsonify(generate_return_dictionary(301, "Invalid Receiver"))

		#check the available balance of the sender and receiver
		sender_balance = check_balance(username)
		receiver_balance = check_balance(receiver) 
		bank_amount = check_balance("BANK")

		update_balance("BANK", bank_amount + 1)
		update_balance(receiver, receiver_balance + amount)
		update_balance(username, sender_balance - amount - 1) 

		return jsonify(generate_return_dictionary(200, "Transfer successful"))


class Balance(Resource):

	def post(self):
		postedData = request.get_json()
		username = postedData['username']
		password = postedData['password']

		retJson, error = verify_cred_with_msg(username, password)
		if error:
			return jsonify(retJson)

		# balance = check_balance(username)
		# debt = check_debt(username)
		# retJson = {
		# 	"status": 200,
		#	"Username": username
		# 	"Balance": balance,
		# 	"Debt": debt
		# }
		# return jsonify(retJson)

		"""OR Alternatively"""
		retJson = users.find({
			"Username": username
			}, {
				"Password": 0,
				"_id": 0 
			})[0]  # "Password": 0, "_id": 0 hides these fields so this returns everything except the fields specified
		return jsonify(retJson)


class TakeLoan(Resource):

	def post(self):
		postedData = request.get_json()
		username = postedData['username']
		password = postedData['password']
		amount = postedData['amount']

		retJson, error = verify_cred_with_msg(username, password)
		if error:
			return jsonify(retJson)

		balance = check_balance(username)
		debt = check_debt(username)

		update_balance(username, balance + amount) #The loan amount is added to the users current balance
		update_debt(username, debt + amount) #The loan amount is added as debt to the user

		return jsonify(generate_return_dictionary(200, "Loan Borrowed Successfully"))


class PayLoan(Resource):

	def post(self):
		postedData = request.get_json()
		username = postedData['username']
		password = postedData['password']
		amount = postedData['amount']

		retJson, error = verify_cred_with_msg(username, password)
		if error:
			return jsonify(retJson)

		balance = check_balance(username)
		if balance < amount:
			return jsonify(generate_return_dictionary(303, "Insufficient Funds"))

		debt = check_debt(username)
		update_balance(username, balance - amount)
		update_debt(username, debt - amount)

		return jsonify(generate_return_dictionary(200, "Loan Payment Successful"))


api.add_resource(Register, '/register')
api.add_resource(Credit, '/credit')
api.add_resource(Tranfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeloan')
api.add_resource(PayLoan, '/payloan')

if __name__ == '__main__':
	app.run(host='0.0.0.0')


