import random
import json
import discord
import re

Verbosity = 0
UserFile = 'users.json'
SecurityFile = 'roll.json'

# Read in Security File
with open(SecurityFile,"r") as f:
	Security = json.load(f)

TOKEN = Security["Token"]

def Message(msg,lvl=0):
	# Send a message based on Debug level
	if lvl <= Verbosity:
		print(msg)

def IsDieRoll(input):
	# Tell us if this string is like a series of die rolls
	if re.fullmatch("[+-]*(([0-9]*d[0-9]+[+-]?)|([0-9]+[+-]?))+",input.strip()):
		return True
	else:
		return False

def rollToken(Token):
	# Roll the numbers for a single die type

	# the operator to use (+,-)
	oper = Token[0]

	# if it has a "d", that means there are dice, otherwise it's just a number to add
	if "d" in Token:
		# die to roll
		parts=Token[1:].split("d")
		high=int(parts[1])
		low=1
		if parts[0] is None or parts[0] == "":
			num = 1
		else:
			num=int(parts[0])
	else:
		# just a simple number to add/sutract
		high=int(Token[1:])
		low=high
		num=1

	info = Token + " "
	total = 0
	# roll for as many of this type of die that is called for
	for x in range(num):
		# if they are equal, it must be a simple number
		if low == high:
			roll = high
		else:
			roll = random.randint(low,high)
			info += "({roll})".format(roll=roll)
		# decide if we add or subtract
		if oper == "+":
			total+=roll
		else:
			total-=roll

	return total, info.strip()


def rollem(input):
	# Stack up all of the dice that need to be rolled and get a total
	try:
		parts = input.split()
		# Description is all words past the 2nd one, we join them back up with spaces
		description = " ".join(parts[2:])
		Message(description,2)

		# I decided to add pipes in front of pluses and minuses to be able to split it and keep the sign with it
		rollstr = "+"+parts[1].replace("+","|+").replace("-","|-")
		rolls=rollstr.split("|")
		Message(rolls,2)

		total = 0
		info = ""

		# Run through the whole list and total everything up.
		for roll in rolls:
			subtotal, substr = rollToken(roll)
			total += subtotal
			info +=  " " + substr

		retstr = ""
		# put in a description if one was given.
		if len(description) > 0:
			retstr += description + " => "
		# Total up the roll and report
		retstr += "{rollInfo} = {Total}".format(rollInfo=info.strip(),Total=total)
		Message(retstr,1)

	except Exception as e:
		retstr = "We didn't like that string for some reason."

	return retstr


def parse(input,author):
	# parse the input string from the message so that we can see what we need to do
	parts = input.split()
	Message(parts,1)

	retstr = None

	#drop out if this is not a Roll command
	if len(parts) == 0 or parts[0].upper() not in ['!','!R','!ROLL','/','/R','/ROLL','\\','\\R','\\ROLL']:
		return None

	# If this is a Multi-Command, run each command separately and stack them together, and return that
	lines = input.split(";")
	if len(lines) > 1 and parts[1].upper() not in ["DEFINE","LOAD"]:
		output = author + " rolls:\n"
		for line in lines:
			output += parse(line.strip(),author) + "\n"
		return output.strip()

	try:
		if parts[1].upper() == "DEFINE":
			# read in Database of User Macros
			with open(UserFile,"r") as f:
				Users = json.load(f)
			# initialize this user if he's not in the DB
			if author not in Users:
				Users[author] = {}
			#save this macro for the user
			Users[author][parts[2]] = "! " + " ".join(parts[3:])
			# save to DB file for next time
			with open(UserFile,"w") as f:
				f.write(json.dumps(Users,indent=2))
			#give user message so he knows it's saved
			retstr = "{Author} saved '{macro}' as '{definition}'".format(Author=author,macro=parts[2],definition=Users[author][parts[2]])
		elif parts[1].upper() == "ECHO":
			retstr = "{Author}: {rollreturn}".format(Author=author,rollreturn=" ".join(parts[2:]))
		elif parts[1].upper() == "USE":
			# get User Macro DB from file
			with open(UserFile,"r") as f:
				Users = json.load(f)
			# run the macro
			retstr = parse(Users[author][parts[2]],author)
		elif parts[1].upper() == "LIST":
			# get User Macro DB from file
			with open(UserFile,"r") as f:
				Users = json.load(f)
			# initialize this user if he's not in the DB
			if author not in Users:
				Users[author] = {}
			# build list of stored commands
			retstr = "\n{Author}'s Macros:".format(Author=author)
			for key,value in Users[author].items():
				retstr += "\n{MacroName}:\t{MacroText}".format(MacroName=key,MacroText=value)
		elif parts[1].upper() == "LOAD":
			# get User Macro DB from file
			with open(UserFile,"r") as f:
				Users = json.load(f)
			# initialize this user if he's not in the DB
			if author not in Users:
				Users[author] = {}
			# build list of stored commands
			if len(parts) > 2 and parts[2].lstrip()[0] == "{":
				Users[author].update(json.loads(" ".join(parts[2:])))
				retstr = "\n{Author} added or updated Macros".format(Author=author)
				# save to DB file for next time
				with open(UserFile,"w") as f:
					f.write(json.dumps(Users,indent=2))
			else:
				retstr = "\n{Author}'s Macro string was not recognized JSON:".format(Author=author)
		elif parts[1].upper() in ["HELP"]:
			retstr = '''
My Key word is "!", "!r", "!roll" or "\\", "\\r", "\\roll"
Make simple roll with: "! 2d6+4 Sword Damage"
Save a macro: "! define init 1d20+5 Intitative"
Use a macro: "! use init" or just "! init"
Echo some text: "! echo Suck it monsters!!!!"
List your existing macros: "! list"
Load up set of macros: "! load {'dex':'! 1d20+9 Dex Save','str':'! 1d20+5 Str Save'}""
Can roll multiple kinds of dice: "! 3d6+2d4-4"
Use a semi-colon to execute multiple commands! '''
		elif IsDieRoll(parts[1]):
			# Looks like a manual die Rolle, Get output for roll string
			retstr = "{Author}: {rollreturn}".format(Author=author,rollreturn=rollem(input))
		else:
			# This doesn't match anything we know, so let's see if it is a Macro
			# get User Macro DB from file
			with open(UserFile,"r") as f:
				Users = json.load(f)
			Message(Users[author].keys(),2)
			if parts[1] in Users[author].keys():
				# run the macro
				retstr = parse(Users[author][parts[1]],author)
			else:
				# must be a nonsense string
				retstr = "String Doesn't parse correctly."
	except Exception as e:
		retstr = None

	return retstr


#########################################################################
# Main Program
#########################################################################


client = discord.Client()

# This block is the work horse part
@client.event
async def on_message(message):
	# we do not want the bot to reply to itself
	if message.author == client.user:
		return
	# get the output for the given message
	output = parse(message.content,message.author.display_name)
	#Send you reply if there is something.
	if output is not None:
		await client.send_message(message.channel, output)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

client.run(TOKEN)
