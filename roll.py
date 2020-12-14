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

def replaceVars(input,varlist):
	InStr=input.strip()
	for key in varlist.keys():
		InStr = InStr.replace("{"+key+"}",varlist[key])
	return InStr

def IsDieRoll(input,varlist):
	# First, let's replace any variables in the string
	RollStr=replaceVars(input.strip(),varlist)
	# Tell us if this string is like a series of die rolls
	if re.fullmatch("[+-]*(([0-9]*d[0-9]+[+-]?)|([0-9]+[+-]?))+",RollStr):
		return True
	else:
		return False

def rollToken(Token,varlist):
	# Roll the numbers for a single die type
	if Token[0]=='{':
		TokenStr=Token[1:][0:-1]
		Token=varlist[TokenStr]
		TokenStr="{Value}({VarName})".format(Value=Token,VarName=TokenStr)
	else:
		TokenStr=Token

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

	info = TokenStr + " "
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


def rollem(input,varlist):
	# Stack up all of the dice that need to be rolled and get a total
	Message("RollEm: '{text}' : {VarList}".format(text=input,VarList=json.dumps(varlist)),1)
	try:
		parts = input.split()
		# Description is all words past the 2nd one, we join them back up with spaces
		description = " ".join(parts[2:])
		Message(description,2)

		# I decided to add pipes in front of pluses and minuses to be able to split it and keep the sign with it
		rollstr = "+"+parts[1].replace("+","|+").replace("-","|-").replace("{","|{").replace("}","}|")
		#remove any accidentally created blank roll tokens
		rollsd=rollstr.split("|")
		rolls = []
		for rstr in rollsd:
			if rstr != "": rolls.append(rstr)

		if rolls[-1]=='':
			rolls=rolls[0:-1]
		Message(rolls,2)

		total = 0
		info = ""

		# Run through the whole list and total everything up.
		for roll in rolls:
			subtotal, substr = rollToken(roll,varlist)
			total += subtotal
			info +=  " " + substr

		retstr = ""
		# put in a description if one was given.
		if len(description) > 0:
			retstr += description + " => "
		# Total up the roll and report
		retstr += "{rollInfo} = **{Total}**".format(rollInfo=info.strip(),Total=total)
		Message(retstr,1)

	except Exception as e:
		retstr = "We didn't like that string for some reason."

	return retstr

def refreshDataFile(author):
	# read in Database of User Macros
	with open(UserFile,"r") as f:
		Users = json.load(f)
	# initialize this user if he's not in the DB
	if author not in Users:
		Users[author] = {"macros":{},"vars":{}}
	if "macros" not in Users[author]:
		Users[author]["macros"] = {}
	if "vars" not in Users[author]:
		Users[author]["vars"] = {}
	return Users

def parse(input,author,MultiLine=0):
	# parse the input string from the message so that we can see what we need to do
	parts = input.strip().split()
	Message(parts,1)

	retstr = None
	if MultiLine == 1:
		AuthorName = "   "
	else:
		AuthorName = author

	#drop out if this is not a Roll command
	if len(parts) == 0 or parts[0].upper() not in ['!','!R','!ROLL','/','/R','/ROLL','\\','\\R','\\ROLL']:
		#Try to make a command if first character is !
		if parts[0][0]=="!":
			pt=["!",parts[0][1:],parts[1:]]
			parts=pt
		else:
			Message("Not a command",1)
			return None

	# If this is a Multi-Command, run each command separately and stack them together, and return that
	lines = input.split(";")
	Message(lines,1)
	Users=refreshDataFile(author)
	if len(lines) > 1 and parts[1].upper() not in ["DEFINE","LOAD"]:
		Message("MultiLine",1)
		output = ""
		if MultiLine == 0:
			output += author + " rolls:\n"
		for line in lines:
			output += parse(line.strip(),author,1) + "\n"
		return output.strip('\n')

	try:
		Message("Command: "+parts[1].upper(),1)
		if parts[1].upper() == "DEFINE":
			Users=refreshDataFile(author)
			#save this macro for the user
			Users[author]['macros'][parts[2]] = "! " + " ".join(parts[3:])
			# save to DB file for next time
			with open(UserFile,"w") as f:
				f.write(json.dumps(Users,indent=2))
			#give user message so he knows it's saved
			retstr = "{Author} saved '{macro}' as '{definition}'".format(Author=author,macro=parts[2],definition=Users[author][parts[2]])
		if parts[1].upper() == "SET":
			Users=refreshDataFile(author)
			#save this variable for the user
			Users[author]['vars'][parts[2]] = parts[3]
			# save to DB file for next time
			with open(UserFile,"w") as f:
				f.write(json.dumps(Users,indent=2))
			#give user message so he knows it's saved
			retstr = "{Author} saved '{variable}' as '{definition}'".format(Author=author,variable=parts[2],definition=parts[3])
		elif parts[1].upper() == "ECHO":
			retstr = "{Author}: {rollreturn}".format(Author=AuthorName,rollreturn=replaceVars(" ".join(parts[2:]),Users[author]['vars']))
		elif parts[1].upper() == "USE":
			Users=refreshDataFile(author)
			# run the macro
			retstr = parse(Users[author]['macros'][parts[2]],author,MultiLine)
		elif parts[1].upper() == "LIST":
			Users=refreshDataFile(author)
			# build list of stored commands
			retstr = "\n{Author}'s Macros:".format(Author=author)
			for key,value in Users[author]['macros'].items():
				retstr += "\n{MacroName}:\t{MacroText}".format(MacroName=key,MacroText=value)
			retstr += "\n{Author}'s Variables:".format(Author=author)
			for key,value in Users[author]['vars'].items():
				retstr += "\n{MacroName}:\t{MacroText}".format(MacroName=key,MacroText=value)
		elif parts[1].upper() == "LOAD":
			Users=refreshDataFile(author)
			# build list of stored commands
			if len(parts) > 2 and parts[2].lstrip()[0] == "{":
				Users[author]['macros'].update(json.loads(" ".join(parts[2:])))
				retstr = "\n{Author} added or updated Macros".format(Author=author)
				# save to DB file for next time
				with open(UserFile,"w") as f:
					f.write(json.dumps(Users,indent=2))
			else:
				retstr = "\n{Author}'s Macro string was not recognized JSON:".format(Author=author)
		elif parts[1].upper() in ["HELP"]:
			retstr = '''
My Key words are "!", "!r", "!roll" or "\\", "\\r", "\\roll"
Make simple roll with:```/roll 2d6+4```
Add description text:```/roll 2d6+4 Sword Damage```
Print some text with no roll:```! echo Suck it monsters!!!!```
Can roll multiple kinds of dice:```! 3d6+2d4-4```
Use a semi-colon to execute multiple commands!
***Macros***
**Save**:```! define init 1d20+5 Intitative```
**Use**:```! use init```or just ```! init```
**List** your existing macros:```! list```
**Load** up set of macros:```! load {'dex':'! 1d20+9 Dex Save','str':'! 1d20+5 Str Save'}```
***Variables***
**Set**:```! set Proficiency +4```
**Use**:```! d20{Proficiency}+1 Sword to Hit```
Variables are essentially string replacements.  If you need to add or subtract, make sure to put plus and minus signs in the variable, or in the macro, but not both.

Macros can call macros.  Example:
A Gun Attack:```/roll define gun 1d20+12 Gun to hit```
Damage for the gun attack:```/roll define gun-dam 1d8+6 Piercing Damage```
Combo macro that uses the other 2 multiple times:```/roll define atk echo **Normal Gun Attack**; ! echo 1st Shot:; ! use gun; ! use gun-dam; ! echo 2nd Shot:; ! use gun; ! use gun-dam```
'''
		elif IsDieRoll(parts[1],Users[author]['vars']):
			# Looks like a manual die Rolle, Get output for roll string
			retstr = "{Author}: {rollreturn}".format(Author=AuthorName,rollreturn=rollem(input,Users[author]['vars']))
		else:
			# This doesn't match anything we know, so let's see if it is a Macro
			# get User Macro DB from file
			Message("Load file",1)
			Users=refreshDataFile(author)
			Message("File Loaded",1)
			#Message(Users[author]['macros'].keys(),2)
			if parts[1] in Users[author]['macros'].keys():
				# run the macro
				retstr = parse(Users[author]['macros'][parts[1]],author,MultiLine)
			else:
				# must be a nonsense string
				retstr = '{Author}, your command was not understood.'.format(Author=author)
	except Exception as e:
		print(e)
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
	if output is not None:
		await message.channel.send(output)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

client.run(TOKEN)
